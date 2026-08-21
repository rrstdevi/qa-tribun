from abc import ABC, abstractmethod
from typing import List
from models import TestRequest, ValidationResult

class BaseValidator(ABC):
    """
    Abstract base class for all validators.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the validator"""
        pass

    @abstractmethod
    def validate(self, request: TestRequest) -> List[ValidationResult]:
        """
        Perform validation logic on the given request.
        """
        pass

class BaseCrossValidator(ABC):
    """
    Abstract base class for cross-validators that analyze multiple requests
    and can modify existing validation contexts.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the cross validator"""
        pass

    @abstractmethod
    def validate_all(self, requests: List[TestRequest], context: dict):
        """
        Perform cross-validation logic.
        context is a Dict[TestRequest, List[ValidationResult]]
        """
        pass
