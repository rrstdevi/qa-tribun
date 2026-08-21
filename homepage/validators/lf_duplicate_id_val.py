from typing import List
from QA.models import TestRequest, ValidationResult
from QA.validators.base_validator import BaseValidator

class LFDuplicateIdValidator(BaseValidator):
    @property
    def name(self) -> str:
        return "Latest Feed Duplicate ID Detection"

    def validate(self, request: TestRequest) -> List[ValidationResult]:
        results = []
        if request.endpoint != "/latest_feed":
            return results
            
        seen_ids = set()
        for i, article in enumerate(request.articles):
            if article.id in seen_ids:
                results.append(ValidationResult(
                    self.name, "FAIL", f"Duplicate ID {article.id} found at index {i}"
                ))
                return results
            if article.id is not None:
                seen_ids.add(article.id)
                
        results.append(ValidationResult(self.name, "PASS", "No duplicate article IDs found in response."))
        return results
