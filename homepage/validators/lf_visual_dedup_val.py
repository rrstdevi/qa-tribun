from typing import List
from QA.models import TestRequest, ValidationResult
from QA.validators.base_validator import BaseValidator

class LFVisualDedupValidator(BaseValidator):
    @property
    def name(self) -> str:
        return "Latest Feed Visual Deduplication"

    def validate(self, request: TestRequest) -> List[ValidationResult]:
        results = []
        if request.endpoint != "/latest_feed":
            return results
            
        if len(request.articles) < 2:
            return results
            
        for i in range(len(request.articles) - 1):
            curr_foto = request.articles[i].raw_json.get("foto")
            next_foto = request.articles[i+1].raw_json.get("foto")
            
            if curr_foto and next_foto and curr_foto == next_foto:
                results.append(ValidationResult(
                    self.name, "FAIL", 
                    f"Adjacent articles at index {i} and {i+1} have identical image URL: {curr_foto}"
                ))
                return results
                
        results.append(ValidationResult(self.name, "PASS", "No visually duplicate adjacent articles found."))
        return results
