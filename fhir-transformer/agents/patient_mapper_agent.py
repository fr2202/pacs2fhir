"""
Patient Mapper Agent
Maps PACS Patient fields to a FHIR R4 Patient resource (dict).
"""
import uuid
from typing import List, Optional, Tuple

from agents.base_agent import BaseFHIRMapper
from config.settings import PATIENT_ID_SYSTEM, FHIR_BASE_URL, ORGANIZATION_ID
from utils.date_utils import to_fhir_date


class PatientMapperAgent(BaseFHIRMapper):
    """Produces a FHIR R4 Patient dict from raw PACS patient data."""

    @property
    def resource_type(self) -> str:
        return "Patient"

    def validate_output(self, resource: dict) -> Tuple[bool, List[str]]:
        required = ["resourceType", "id", "identifier"]
        errors = [f"Missing: {f}" for f in required if not resource.get(f)]
        return len(errors) == 0, errors

    def map(self, patient_id: str, birthdate: str) -> dict:
        fhir_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{PATIENT_ID_SYSTEM}|{patient_id}"))
        birth_fhir = to_fhir_date(birthdate)

        resource: dict = {
            "resourceType": "Patient",
            "id": fhir_id,
            "meta": {
                "profile": [
                    "http://hl7.org/fhir/StructureDefinition/Patient"
                ]
            },
            "identifier": [
                {
                    "use": "official",
                    "system": PATIENT_ID_SYSTEM,
                    "value": patient_id,
                    "assigner": {"reference": f"Organization/{ORGANIZATION_ID}"}
                }
            ],
            "active": True,
            "managingOrganization": {
                "reference": f"Organization/{ORGANIZATION_ID}"
            },
        }

        if birth_fhir:
            resource["birthDate"] = birth_fhir

        return resource

    def get_patient_id(self, patient_id: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{PATIENT_ID_SYSTEM}|{patient_id}"))
