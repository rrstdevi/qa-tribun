from typing import List
from datetime import datetime
from QA.models import TestRequest, ValidationResult
from QA.validators.base_validator import BaseValidator

class LFSortingValidator(BaseValidator):
    @property
    def name(self) -> str:
        return "Latest Feed Chronological Sorting"

    def validate(self, request: TestRequest) -> List[ValidationResult]:
        results = []
        if request.endpoint != "/latest_feed":
            return results
            
        if len(request.articles) <= 1:
            return results
            
        errors = []
        previous_date = None
        previous_id = None
        
        for article in request.articles:
            try:
                date_str = article.publish_date.replace("Z", "+00:00") if article.publish_date else ""
                if not date_str:
                    continue
                pub_date = datetime.fromisoformat(date_str)
                
                if previous_date is not None:
                    if pub_date > previous_date:
                        errors.append(f"Article ID {article.id} ({pub_date}) is newer than previous ID {previous_id} ({previous_date})")
                
                previous_date = pub_date
                previous_id = article.id
            except Exception as e:
                if previous_date is not None and str(article.publish_date) > str(previous_date):
                    errors.append(f"Article ID {article.id} ({article.publish_date}) is newer than previous ID {previous_id} ({previous_date}) (String comparison)")
                previous_date = article.publish_date
                previous_id = article.id
                
        if errors:
            results.append(ValidationResult(self.name, "FAIL", "Articles are not properly sorted descending:\n" + "\n".join(errors)))
        else:
            results.append(ValidationResult(self.name, "PASS", "Articles are sorted chronologically (newest to oldest)."))
            
        return results
