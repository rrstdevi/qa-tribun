from typing import List
from models import TestRequest, ValidationResult
from validators.base_validator import BaseValidator

class SectionTitleValidator(BaseValidator):
    @property
    def name(self) -> str:
        return "Section Title Validation"

    def validate(self, request: TestRequest) -> List[ValidationResult]:
        results = []
        
        if request.endpoint not in ["/homepage", "/article"]:
            return results

        if not request.articles:
            return results

        invalid_articles = []
        for article in request.articles:
            st = article.section_title
            
            is_invalid = False
            if st is None:
                is_invalid = True
            elif isinstance(st, str):
                st_clean = st.strip()
                if st_clean == "" or st_clean.lower() == "unknown":
                    is_invalid = True
            else:
                is_invalid = True

            if is_invalid:
                invalid_articles.append({
                    "id": article.id,
                    "title": article.title,
                    "section_title": st
                })

        if invalid_articles:
            msg_lines = ["Ditemukan artikel dengan section_title tidak valid:"]
            for bad in invalid_articles:
                msg_lines.append(f"- ID: {bad['id']} | Title: \"{bad['title']}\" | section_title: {repr(bad['section_title'])}")
            
            detail_msg = "\n".join(msg_lines)
            results.append(ValidationResult(self.name, "FAIL", detail_msg))
        else:
            results.append(ValidationResult(self.name, "PASS", "Seluruh artikel memiliki section_title yang valid"))

        return results
