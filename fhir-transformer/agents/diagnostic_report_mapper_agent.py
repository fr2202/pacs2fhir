"""
DiagnosticReport Mapper Agent
Maps PACS report text + metadata to a FHIR R4 DiagnosticReport resource.
"""
import base64
import uuid
from typing import List, Optional, Tuple

from agents.base_agent import BaseFHIRMapper
from agents.rtf_parser_agent import ParsedRTF
from config.settings import ACCESSION_SYSTEM, ORGANIZATION_ID, FHIR_BASE_URL
from config.code_mappings import get_loinc_for_exam, LOINC_SYSTEM
from utils.date_utils import to_fhir_datetime, to_fhir_instant


class DiagnosticReportMapperAgent(BaseFHIRMapper):
    """Produces a FHIR R4 DiagnosticReport dict from PACS report content."""

    @property
    def resource_type(self) -> str:
        return "DiagnosticReport"

    def validate_output(self, resource: dict) -> Tuple[bool, List[str]]:
        required = ["resourceType", "status", "code", "subject"]
        errors = [f"Missing: {f}" for f in required if not resource.get(f)]
        return len(errors) == 0, errors

    def map(
        self,
        accession_number: str,
        exam_type: str,
        parsed_observation: ParsedRTF,
        parsed_report: ParsedRTF,
        patient_fhir_id: str,
        encounter_fhir_id: Optional[str],
        imaging_study_fhir_id: str,
        validation_timestamp: Optional[str],
        extraction_timestamp: Optional[str],
    ) -> dict:
        fhir_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{ACCESSION_SYSTEM}|DR|{accession_number}"))
        loinc = get_loinc_for_exam(exam_type)

        status = "final" if validation_timestamp else "preliminary"

        # Effective date: prefer RTF date, fallback to validation or extraction timestamp
        effective = to_fhir_datetime(
            parsed_report.exam_date or parsed_observation.exam_date or "",
            parsed_report.exam_time or parsed_observation.exam_time or "",
        )
        if not effective:
            effective = to_fhir_instant(validation_timestamp or extraction_timestamp or "")

        issued = to_fhir_instant(validation_timestamp) if validation_timestamp else None
        last_updated = to_fhir_instant(extraction_timestamp or "") if extraction_timestamp else None

        resource: dict = {
            "resourceType": "DiagnosticReport",
            "id": fhir_id,
            "meta": {
                "profile": [
                    "http://hl7.org/fhir/StructureDefinition/DiagnosticReport"
                ]
            },
            "identifier": [
                {
                    "use": "official",
                    "type": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                                "code": "ACSN",
                                "display": "Accession ID"
                            }
                        ]
                    },
                    "system": ACCESSION_SYSTEM,
                    "value": accession_number,
                    "assigner": {"reference": f"Organization/{ORGANIZATION_ID}"}
                }
            ],
            "status": status,
            "category": [
                {
                    "coding": [
                        {
                            "system": LOINC_SYSTEM,
                            "code": "18748-4",
                            "display": "Diagnostic imaging study"
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": LOINC_SYSTEM,
                        "code": loinc["code"],
                        "display": loinc["display"]
                    }
                ],
                "text": exam_type
            },
            "subject": {
                "reference": f"Patient/{patient_fhir_id}"
            },
            "imagingStudy": [
                {"reference": f"ImagingStudy/{imaging_study_fhir_id}"}
            ],
        }

        if last_updated:
            resource["meta"]["lastUpdated"] = last_updated

        if encounter_fhir_id:
            resource["encounter"] = {"reference": f"Encounter/{encounter_fhir_id}"}

        if effective:
            resource["effectiveDateTime"] = effective

        if issued:
            resource["issued"] = issued

        report_full = self._build_full_text(parsed_observation, parsed_report, exam_type)
        if report_full:
            resource["presentedForm"] = [
                {
                    "contentType": "text/plain;charset=UTF-8",
                    "language": "pt-PT",
                    "data": base64.b64encode(report_full.encode("utf-8")).decode("ascii"),
                    "title": exam_type,
                    "size": len(report_full.encode("utf-8")),
                }
            ]

        conclusion = parsed_report.report_text or parsed_observation.report_text
        if conclusion:
            resource["conclusion"] = conclusion

        return resource

    def _build_full_text(self, obs: ParsedRTF, rep: ParsedRTF, exam_type: str) -> str:
        parts = [f"Exame: {exam_type}"]
        if obs.clinical_info:
            parts.append(f"Informação clínica:\n{obs.clinical_info}")
        elif rep.clinical_info:
            parts.append(f"Informação clínica:\n{rep.clinical_info}")
        if rep.technical_protocol:
            parts.append(f"Protocolo técnico:\n{rep.technical_protocol}")
        if rep.report_text:
            parts.append(f"Relatório:\n{rep.report_text}")
        elif obs.report_text:
            parts.append(f"Relatório:\n{obs.report_text}")
        if rep.radiologist:
            parts.append(f"Assinado por: {rep.radiologist}")
        return "\n\n".join(p for p in parts if p.strip() != f"Exame: {exam_type}" or len(parts) == 1)
