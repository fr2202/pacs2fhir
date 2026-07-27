"""
Base Agent
Defines the abstract contract that all FHIR resource mapper components must satisfy.

Every concrete mapper must:
  - Declare which FHIR resource type it produces (resource_type).
  - Be able to validate its own output (validate_output).

This allows the TransformationPipeline to treat all mappers uniformly and
call validate_output() on each one without knowing the concrete type.
"""
from abc import ABC, abstractmethod
from typing import List, Tuple


class BaseFHIRMapper(ABC):
    """Abstract contract for FHIR R4 resource mapper components."""

    @property
    @abstractmethod
    def resource_type(self) -> str:
        """FHIR resource type produced by this mapper (e.g. 'Patient')."""
        ...

    @abstractmethod
    def validate_output(self, resource: dict) -> Tuple[bool, List[str]]:
        """
        Verify that *resource* satisfies the minimum FHIR R4 required fields
        for this mapper's resource type.

        Returns:
            (True, [])           — resource is structurally valid.
            (False, [errors])    — one or more required fields are missing.
        """
        ...
