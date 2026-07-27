"""
ImagingStudy Mapper Agent
Maps PACS AccessionNumber + Exam_Type to a FHIR R4 ImagingStudy resource.
"""
import uuid
from typing import List, Optional, Tuple

from agents.base_agent import BaseFHIRMapper
from config.settings import ACCESSION_SYSTEM, ORGANIZATION_ID, FHIR_BASE_URL
from config.code_mappings import get_loinc_for_exam, LOINC_SYSTEM, DICOM_MODALITY_SYSTEM
from utils.date_utils import to_fhir_datetime


class ImagingStudyMapperAgent(BaseFHIRMapper):
    """Produces a FHIR R4 ImagingStudy dict from PACS report metadata."""

    @property
    def resource_type(self) -> str:
        return "ImagingStudy"

    def validate_output(self, resource: dict) -> Tuple[bool, List[str]]:
        required = ["resourceType", "status", "subject", "identifier"]
        errors = [f"Missing: {f}" for f in required if not resource.get(f)]
        return len(errors) == 0, errors

    def map(
        self,
        accession_number: str,
        exam_type: str,
        patient_fhir_id: str,
        encounter_fhir_id: Optional[str],
        exam_date: Optional[str],
        exam_time: Optional[str],
        extraction_timestamp: Optional[str],
    ) -> dict:
        fhir_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{ACCESSION_SYSTEM}|{accession_number}"))
        loinc = get_loinc_for_exam(exam_type)
        started = to_fhir_datetime(exam_date or "", exam_time or "")

        resource: dict = {
            "resourceType": "ImagingStudy",
            "id": fhir_id,
            "meta": {
                "profile": [
                    "http://hl7.org/fhir/StructureDefinition/ImagingStudy"
                ]
            },
            "status": "available",
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
                    "value": accession_number
                }
            ],
            "modality": [
                {
                    "system": DICOM_MODALITY_SYSTEM,
                    "code": loinc["modality"],
                    "display": loinc["modality"]
                }
            ],
            "subject": {
                "reference": f"Patient/{patient_fhir_id}"
            },
            "description": exam_type,
            "reasonCode": [
                {
                    "coding": [
                        {
                            "system": LOINC_SYSTEM,
                            "code": loinc["code"],
                            "display": loinc["display"]
                        }
                    ],
                    "text": exam_type
                }
            ],
        }

        if encounter_fhir_id:
            resource["encounter"] = {"reference": f"Encounter/{encounter_fhir_id}"}

        if started:
            resource["started"] = started

        return resource

    def get_imaging_study_id(self, accession_number: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{ACCESSION_SYSTEM}|{accession_number}"))
