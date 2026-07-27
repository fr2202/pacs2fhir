"""
Validator Agent
Validates FHIR R4 resources using fhir.resources (Pydantic-based schema validation).
Returns (is_valid, list_of_errors).
"""
from typing import Any, List, Tuple

try:
    from fhir.resources.patient import Patient
    from fhir.resources.encounter import Encounter
    from fhir.resources.imagingstudy import ImagingStudy
    from fhir.resources.diagnosticreport import DiagnosticReport
    from fhir.resources.bundle import Bundle
    from pydantic import ValidationError
    _FHIR_AVAILABLE = True
except ImportError:
    _FHIR_AVAILABLE = False

_RESOURCE_CLASS_MAP = {
    "Patient": "Patient",
    "Encounter": "Encounter",
    "ImagingStudy": "ImagingStudy",
    "DiagnosticReport": "DiagnosticReport",
    "Bundle": "Bundle",
}


class ValidatorAgent:
    """
    Validates a FHIR R4 resource dict.
    Falls back to structural checks if fhir.resources is unavailable.
    """

    def validate(self, resource: dict) -> Tuple[bool, List[str]]:
        resource_type = resource.get("resourceType")
        if not resource_type:
            return False, ["Missing resourceType"]

        if not _FHIR_AVAILABLE:
            return self._structural_validate(resource)

        try:
            cls = self._get_class(resource_type)
            if cls is None:
                return self._structural_validate(resource)
            cls.parse_obj(resource)
            return True, []
        except ValidationError as exc:
            errors = [f"{e['loc']}: {e['msg']}" for e in exc.errors()]
            return False, errors
        except Exception as exc:
            return False, [str(exc)]

    def validate_bundle(self, bundle: dict) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        if bundle.get("resourceType") != "Bundle":
            return False, ["resourceType must be Bundle"]
        if not bundle.get("type"):
            errors.append("Bundle.type is required")
        entries = bundle.get("entry", [])
        for i, entry in enumerate(entries):
            res = entry.get("resource", {})
            ok, errs = self.validate(res)
            if not ok:
                errors.extend([f"entry[{i}].{e}" for e in errs])
        return len(errors) == 0, errors

    def _get_class(self, resource_type: str):
        if not _FHIR_AVAILABLE:
            return None
        mapping = {
            "Patient": Patient,
            "Encounter": Encounter,
            "ImagingStudy": ImagingStudy,
            "DiagnosticReport": DiagnosticReport,
            "Bundle": Bundle,
        }
        return mapping.get(resource_type)

    def _structural_validate(self, resource: dict) -> Tuple[bool, List[str]]:
        errors = []
        rt = resource.get("resourceType")
        required_fields = {
            "Patient": ["resourceType", "identifier"],
            "Encounter": ["resourceType", "status", "class", "subject"],
            "ImagingStudy": ["resourceType", "status", "subject"],
            "DiagnosticReport": ["resourceType", "status", "code", "subject"],
            "Bundle": ["resourceType", "type"],
        }
        for field in required_fields.get(rt, ["resourceType"]):
            if not resource.get(field):
                errors.append(f"Missing required field: {field}")
        return len(errors) == 0, errors
