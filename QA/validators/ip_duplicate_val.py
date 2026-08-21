import re
import unicodedata
from typing import List, Dict, Any
from models import TestRequest, ValidationResult
from validators.base_validator import BaseValidator

class IPDuplicateTitleValidator(BaseValidator):
    """
    Validates that there are no exact duplicate titles when IP is undetected.
    Applies to /homepage and /article.
    """
    @property
    def name(self) -> str:
        return "IP Undetected Duplicate Title Validation"

    def _normalize_text(self, text: str) -> str:
        """
        Normalizes text for equality comparison: lowercase, remove punctuation, 
        trim whitespace, and Unicode NFKD.
        """
        if not text:
            return ""
        
        # Lowercase
        text = text.lower()
        # Unicode normalization
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
        # Remove punctuation
        text = re.sub(r'[^\w\s]', '', text)
        # Trim extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def validate(self, request: TestRequest) -> List[ValidationResult]:
        if not request.articles or request.endpoint not in ["/homepage", "/article"]:
            return []

        # Check if IP is undetected
        undetected_ips = ["0", "0.0.0.0", "", "null", None]
        
        ip_val = request.ip_address
        if isinstance(ip_val, str):
            ip_val = ip_val.strip().lower()
            
        if ip_val not in undetected_ips:
            return []

        violations = []
        # Store articles by normalized title: {normalized_title: [{"id": id, "title": raw_title, "pos": pos}, ...]}
        title_map: Dict[str, List[Dict[str, Any]]] = {}

        for index, article in enumerate(request.articles):
            norm_title = self._normalize_text(article.title)
            if not norm_title:
                continue

            if norm_title not in title_map:
                title_map[norm_title] = []
                
            title_map[norm_title].append({
                "id": article.id,
                "title": article.title,
                "pos": index + 1
            })

        for norm_title, items in title_map.items():
            if len(items) > 1:
                # We found exact duplicates
                violation_data = {
                    "normalized_title": norm_title,
                    "articles": items
                }
                violations.append(violation_data)

        if violations:
            status = "FAIL"
            detail = f"Found {len(violations)} identical title(s) for undetected IP."
        else:
            status = "PASS"
            detail = "No identical titles found for undetected IP."

        raw_data = {
            "violations": violations
        }

        return [ValidationResult(
            validator_name=self.name,
            status=status,
            detail=detail,
            raw_data=raw_data
        )]
