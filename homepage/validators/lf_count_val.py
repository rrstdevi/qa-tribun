from typing import List
from QA.models import TestRequest, ValidationResult
from QA.validators.base_validator import BaseValidator

class LFCountValidator(BaseValidator):
    @property
    def name(self) -> str:
        return "Latest Feed Count Validation"

    def validate(self, request: TestRequest) -> List[ValidationResult]:
        results = []
        if request.endpoint != "/latest_feed":
            return results
            
        num_req = 20
        if "TC-002" in request.scenario:
            num_req = 10
        elif "TC-003" in request.scenario:
            num_req = 8
            
        # Untuk mode mix, karena merupakan gabungan dari localized dan global, limit jumlah maksimal digandakan
        if hasattr(request, 'mode') and request.mode.lower() == "mix":
            num_req *= 2
            
        count = len(request.articles)
        if count <= num_req:
            results.append(ValidationResult(self.name, "PASS", f"Returned {count} articles, expected max {num_req}."))
        else:
            results.append(ValidationResult(self.name, "FAIL", f"Returned {count} articles, which exceeds max {num_req}."))
            
        return results
