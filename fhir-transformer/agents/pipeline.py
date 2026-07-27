"""
Transformation Pipeline
Executes the PACS → FHIR R4 transformation as a linear, ordered sequence of stages.

Architecture — Pipeline pattern with 7 named stages:
    1. RTF Parsing           RTFParserAgent
    2. Patient Mapping       PatientMapperAgent
    3. Encounter Mapping     EncounterMapperAgent      (optional output)
    4. ImagingStudy Mapping  ImagingStudyMapperAgent
    5. DiagnosticReport Map  DiagnosticReportMapperAgent
    6. Bundle Assembly       BundleGeneratorAgent
    7. Bundle Validation     ValidatorAgent

Usage:
    pipeline = TransformationPipeline.build_default()
    result = pipeline.run(inputs, organization_resource)
    if result.success:
        write(result.bundle)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from agents.bundle_generator_agent import BundleGeneratorAgent
from agents.diagnostic_report_mapper_agent import DiagnosticReportMapperAgent
from agents.encounter_mapper_agent import EncounterMapperAgent
from agents.imaging_study_mapper_agent import ImagingStudyMapperAgent
from agents.patient_mapper_agent import PatientMapperAgent
from agents.rtf_parser_agent import RTFParserAgent
from agents.validator_agent import ValidatorAgent
from utils.date_utils import to_fhir_instant


@dataclass
class PipelineInput:
    """All raw fields extracted from a single PACS JSON record."""
    patient_id: str
    birthdate: str
    accession: str
    exam_type: str
    obs_rtf: str
    rep_rtf: str
    validation_ts: str
    extraction_ts: str


@dataclass
class PipelineResult:
    """Outcome of a single TransformationPipeline.run() call."""
    success: bool
    bundle: Optional[dict] = None
    validation_warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None


class TransformationPipeline:
    """
    Executes all 7 transformation stages for a single PACS record.

    Instantiate once per worker process and call run() for each record —
    agent instances are reused across records within the same worker.
    """

    def __init__(
        self,
        rtf_agent: RTFParserAgent,
        patient_agent: PatientMapperAgent,
        encounter_agent: EncounterMapperAgent,
        imaging_agent: ImagingStudyMapperAgent,
        report_agent: DiagnosticReportMapperAgent,
        bundle_agent: BundleGeneratorAgent,
        validator: ValidatorAgent,
    ) -> None:
        self._rtf = rtf_agent
        self._patient = patient_agent
        self._encounter = encounter_agent
        self._imaging = imaging_agent
        self._report = report_agent
        self._bundle = bundle_agent
        self._validator = validator

    @classmethod
    def build_default(cls) -> "TransformationPipeline":
        """Create a pipeline with default (no-config) agent instances."""
        return cls(
            rtf_agent=RTFParserAgent(),
            patient_agent=PatientMapperAgent(),
            encounter_agent=EncounterMapperAgent(),
            imaging_agent=ImagingStudyMapperAgent(),
            report_agent=DiagnosticReportMapperAgent(),
            bundle_agent=BundleGeneratorAgent(),
            validator=ValidatorAgent(),
        )

    def run(self, inputs: PipelineInput, organization: dict) -> PipelineResult:
        """
        Transform one PACS record into a validated FHIR R4 Bundle.

        Returns a PipelineResult. Never raises — errors are captured in result.error.
        """
        try:
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
            last_updated = to_fhir_instant(inputs.extraction_ts) if inputs.extraction_ts else None

            # Stage 1 — RTF Parsing
            parsed_obs = self._rtf.parse(inputs.obs_rtf)
            parsed_rep = self._rtf.parse(inputs.rep_rtf)

            # Stage 2 — Patient Mapping
            patient = self._patient.map(inputs.patient_id, inputs.birthdate)
            if last_updated:
                patient["meta"]["lastUpdated"] = last_updated
            patient_fhir_id = self._patient.get_patient_id(inputs.patient_id)

            # Stage 3 — Encounter Mapping (optional: skipped when no episode_id)
            encounter = self._encounter.map(parsed_obs or parsed_rep, patient_fhir_id)
            encounter_fhir_id = (
                self._encounter.get_encounter_id(parsed_obs.episode_id)
                if encounter and parsed_obs.episode_id
                else None
            )
            if encounter and last_updated:
                encounter["meta"]["lastUpdated"] = last_updated

            # Stage 4 — ImagingStudy Mapping
            imaging = self._imaging.map(
                accession_number=inputs.accession,
                exam_type=inputs.exam_type,
                patient_fhir_id=patient_fhir_id,
                encounter_fhir_id=encounter_fhir_id,
                exam_date=parsed_obs.exam_date or parsed_rep.exam_date,
                exam_time=parsed_obs.exam_time or parsed_rep.exam_time,
                extraction_timestamp=inputs.extraction_ts,
            )
            if not imaging.get("started") and last_updated:
                imaging["started"] = last_updated
            if last_updated:
                imaging["meta"]["lastUpdated"] = last_updated
            imaging_fhir_id = self._imaging.get_imaging_study_id(inputs.accession)

            # Stage 5 — DiagnosticReport Mapping
            report = self._report.map(
                accession_number=inputs.accession,
                exam_type=inputs.exam_type,
                parsed_observation=parsed_obs,
                parsed_report=parsed_rep,
                patient_fhir_id=patient_fhir_id,
                encounter_fhir_id=encounter_fhir_id,
                imaging_study_fhir_id=imaging_fhir_id,
                validation_timestamp=inputs.validation_ts,
                extraction_timestamp=inputs.extraction_ts,
            )

            # Stage 6 — Bundle Assembly
            org_with_meta = {
                **organization,
                "meta": {**organization["meta"], "lastUpdated": last_updated or now_str},
            }
            bundle = self._bundle.build(
                patient=patient,
                encounter=encounter,
                imaging_study=imaging,
                diagnostic_report=report,
                organization=org_with_meta,
            )

            # Stage 7 — Bundle Validation
            ok, warnings = self._validator.validate_bundle(bundle)
            return PipelineResult(
                success=True,
                bundle=bundle,
                validation_warnings=warnings if not ok else [],
            )

        except Exception as exc:
            return PipelineResult(success=False, error=str(exc))
