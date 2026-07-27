"""
Encounter Mapper Agent
Maps PACS scheduling data (Agendamento) to a FHIR R4 Encounter resource.
"""
import uuid
from typing import List, Optional, Tuple

from agents.base_agent import BaseFHIRMapper
from agents.rtf_parser_agent import ParsedRTF
from config.settings import ENCOUNTER_SYSTEM, ORGANIZATION_ID, FHIR_BASE_URL
from utils.date_utils import to_fhir_datetime


class EncounterMapperAgent(BaseFHIRMapper):
    """Produces a FHIR R4 Encounter dict from parsed RTF scheduling data."""

    @property
    def resource_type(self) -> str:
        return "Encounter"

    def validate_output(self, resource: dict) -> Tuple[bool, List[str]]:
        required = ["resourceType", "status", "class", "subject"]
        errors = [f"Missing: {f}" for f in required if not resource.get(f)]
        return len(errors) == 0, errors

    def map(self, parsed: ParsedRTF, patient_fhir_id: str) -> Optional[dict]:
        if not parsed.episode_id:
            return None

        fhir_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{ENCOUNTER_SYSTEM}|{parsed.episode_id}"))
        period_start = to_fhir_datetime(parsed.exam_date or "", parsed.exam_time or "")

        resource: dict = {
            "resourceType": "Encounter",
            "id": fhir_id,
            "meta": {
                "profile": [
                    "http://hl7.org/fhir/StructureDefinition/Encounter"
                ]
            },
            "status": "finished",
            "class": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": "AMB",
                "display": "ambulatory"
            },
            "identifier": [
                {
                    "use": "official",
                    "system": ENCOUNTER_SYSTEM,
                    "value": parsed.episode_id
                }
            ],
            "subject": {
                "reference": f"Patient/{patient_fhir_id}"
            },
            "serviceProvider": {
                "reference": f"Organization/{ORGANIZATION_ID}"
            },
        }

        if period_start:
            resource["period"] = {"start": period_start}

        if parsed.cabinet:
            resource["location"] = [
                {
                    "location": {
                        "display": f"Gabinete {parsed.cabinet}"
                    },
                    "status": "completed"
                }
            ]

        return resource

    def get_encounter_id(self, episode_id: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{ENCOUNTER_SYSTEM}|{episode_id}"))
