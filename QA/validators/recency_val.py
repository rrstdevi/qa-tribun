from typing import List
from datetime import datetime
from models import TestRequest, ValidationResult
from validators.base_validator import BaseValidator
import config

class RecencyValidator(BaseValidator):
    @property
    def name(self) -> str:
        return "Recency Validation"

    def validate(self, request: TestRequest) -> List[ValidationResult]:
        results = []
        
        overall_status = "PASS"
        detail_msg = ""
        
        top_news_details = []
        other_details = []
        
        # Create aware datetime for "now"
        now = datetime.now().astimezone()

        for idx, article in enumerate(request.articles):
            try:
                # Parse ISO 8601 string, handle timezone appropriately.
                pub_date = datetime.fromisoformat(article.publish_date)
                age_hours = (now - pub_date).total_seconds() / 3600
                age_days = (now - pub_date).days
                
                # Check based on type
                if article.type == "top-news":
                    if request.endpoint == "/homepage":
                        max_val = config.RECENCY_TOP_NEWS_MAX_DAYS
                        age_val = age_days
                        unit = "days"
                    else:
                        max_val = config.RECENCY_TOP_NEWS_MAX_HOURS
                        age_val = age_hours
                        unit = "hours"

                    status = "PASS"
                    if age_val > max_val:
                        status = "FAIL"
                        if overall_status != "ERROR":
                            overall_status = "FAIL"
                    
                    if unit == "hours":
                        top_news_details.append(f"- ID: {article.id} | Age: {age_val:.1f} {unit} | Max: {max_val} {unit} | {status}")
                    else:
                        top_news_details.append(f"- ID: {article.id} | Age: {age_val} {unit} | Max: {max_val} {unit} | {status}")
                        
                elif article.type in ["personalized", "similarity"]:
                    if request.endpoint == "/homepage":
                        max_val = config.RECENCY_PERSONALIZED_MAX_DAYS
                        age_val = age_days
                        unit = "days"
                    else:
                        max_val = config.RECENCY_PERSONALIZED_MAX_HOURS
                        age_val = age_hours
                        unit = "hours"

                    status = "PASS"
                    if age_val > max_val:
                        status = "FAIL"
                        if overall_status != "ERROR":
                            overall_status = "FAIL"
                    if unit == "hours":
                        other_details.append(f"- ID: {article.id} | Age: {age_val:.1f} {unit} | Max: {max_val} {unit} | {status}")
                    else:
                        other_details.append(f"- ID: {article.id} | Age: {age_val} {unit} | Max: {max_val} {unit} | {status}")
            except Exception as e:
                overall_status = "ERROR"
                detail_msg += f"Failed to parse date for article [{article.id}]: {str(e)}\n"

        if overall_status == "PASS":
            detail_msg = "PASS: Recency validation is valid\n\n" + detail_msg
        else:
            detail_msg = f"{overall_status}: Recency validation failed or encountered errors\n\n" + detail_msg
            
        if top_news_details:
            detail_msg += "Top News Articles:\n" + "\n".join(top_news_details) + "\n\n"
        if other_details:
            detail_msg += "Personalized/Similarity Articles:\n" + "\n".join(other_details) + "\n"

        results.append(ValidationResult(self.name, overall_status, detail_msg.strip()))

        return results

