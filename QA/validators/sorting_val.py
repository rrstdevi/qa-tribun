from typing import List
from datetime import datetime
from models import TestRequest, ValidationResult
from validators.base_validator import BaseValidator

class SortingValidator(BaseValidator):
    @property
    def name(self) -> str:
        return "Sorting Validation"

    def validate(self, request: TestRequest) -> List[ValidationResult]:
        results = []
        
        # Only validate sorting for /article endpoint (detail article)
        if request.endpoint != "/article":
            return results
            
        if not request.articles or len(request.articles) <= 1:
            return results
            
        overall_status = "PASS"
        detail_msg = "PASS: Articles are sorted from newest to oldest\n"
        
        previous_date = None
        previous_id = None
        
        errors = []
        
        for article in request.articles:
            try:
                # Parse ISO 8601 string
                pub_date = datetime.fromisoformat(article.publish_date)
                
                if previous_date is not None:
                    if pub_date > previous_date:
                        overall_status = "FAIL"
                        errors.append(f"- Article ID {article.id} ({pub_date.strftime('%Y-%m-%d %H:%M:%S')}) is newer than previous Article ID {previous_id} ({previous_date.strftime('%Y-%m-%d %H:%M:%S')})")
                
                previous_date = pub_date
                previous_id = article.id
            except Exception as e:
                if overall_status != "FAIL":
                    overall_status = "ERROR"
                errors.append(f"- Failed to parse date for article [{article.id}]: {str(e)}")
                
        if overall_status != "PASS":
            detail_msg = f"{overall_status}: Articles are not properly sorted from newest to oldest\n\n"
            detail_msg += "\n".join(errors)

        results.append(ValidationResult(self.name, overall_status, detail_msg.strip()))

        return results
