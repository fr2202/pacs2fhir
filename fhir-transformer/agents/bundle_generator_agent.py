"""
Bundle Generator Agent
Assembles a FHIR R4 transaction Bundle from individual resource dicts.
HAPI FHIR compatible: no ifNoneExist on PUT, includes Bundle.timestamp.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from config.settings import FHIR_BASE_URL


class BundleGeneratorAgent:
    """Creates a FHIR R4 Bundle (transaction) from a set of resources."""

    def build(
        self,
        patient: dict,
        encounter: Optional[dict],
        imaging_study: dict,
        diagnostic_report: dict,
        organization: dict,
    ) -> dict:
        bundle_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        entries = []

        entries.append(self._make_entry(organization, "PUT"))
        entries.append(self._make_entry(patient, "PUT"))
        if encounter:
            entries.append(self._make_entry(encounter, "PUT"))
        entries.append(self._make_entry(imaging_study, "PUT"))
        entries.append(self._make_entry(diagnostic_report, "PUT"))

        return {
            "resourceType": "Bundle",
            "id": bundle_id,
            "meta": {
                "lastUpdated": now,
                "profile": [
                    "http://hl7.org/fhir/StructureDefinition/Bundle"
                ]
            },
            "type": "transaction",
            "timestamp": now,
            "entry": entries,
        }

    def _make_entry(self, resource: dict, method: str) -> dict:
        rt = resource["resourceType"]
        rid = resource["id"]
        # ifNoneExist is only valid on POST (conditional create), not PUT.
        # HAPI FHIR rejects transaction bundles that use ifNoneExist on PUT.
        return {
            "fullUrl": f"{FHIR_BASE_URL}/{rt}/{rid}",
            "resource": resource,
            "request": {
                "method": method,
                "url": f"{rt}/{rid}",
            },
        }
