from typing import List
from QA.models import TestRequest, ValidationResult
from QA.validators.base_validator import BaseValidator

class LFResilienceValidator(BaseValidator):
    @property
    def name(self) -> str:
        return "Latest Feed Redis Resilience"

    def validate(self, request: TestRequest) -> List[ValidationResult]:
        results = []
        if request.endpoint != "/latest_feed":
            return results
            
        for article in request.articles:
            if article.type == "default-value":
                results.append(ValidationResult(
                    self.name, "WARNING", "FALLBACK DETECTED: Response served from Redis fallback (default-value)."
                ))
                return results
                
        results.append(ValidationResult(self.name, "PASS", "Primary database is active (no fallback detected)."))
        return results
