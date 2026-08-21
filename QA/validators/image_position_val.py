from typing import List, Dict, Any
from models import TestRequest, ValidationResult
from validators.base_validator import BaseValidator

class ImagePositionValidator(BaseValidator):
    """
    Validates that identical images are not placed adjacently.
    Applies to both /homepage and /article recommendations.
    """
    @property
    def name(self) -> str:
        return "Duplicate Image URL Position Validation"

    def validate(self, request: TestRequest) -> List[ValidationResult]:
        if not request.articles or request.endpoint not in ["/homepage", "/article"]:
            return []

        violations = []
        # Store positions for each image URL: {url: [{"id": id, "title": title, "pos": pos}, ...]}
        image_map: Dict[str, List[Dict[str, Any]]] = {}

        for index, article in enumerate(request.articles):
            foto_url = article.raw_json.get("foto")
            
            # Skip empty, null, "null", or None image URLs
            if not foto_url or str(foto_url).strip().lower() == "null":
                continue
                
            foto_url = str(foto_url).strip()
            if not foto_url:
                continue

            if foto_url not in image_map:
                image_map[foto_url] = []
                
            image_map[foto_url].append({
                "id": article.id,
                "title": article.title,
                "pos": index + 1  # Using 1-based indexing for reporting
            })

        # Evaluate positions
        for url, items in image_map.items():
            if len(items) > 1:
                # Sort by position just in case
                items.sort(key=lambda x: x["pos"])
                
                # Check adjacent items
                for i in range(len(items) - 1):
                    item1 = items[i]
                    item2 = items[i+1]
                    
                    distance = abs(item1["pos"] - item2["pos"])
                    if distance == 1:
                        violation_data = {
                            "image_url": url,
                            "article_1": item1["id"],
                            "article_2": item2["id"],
                            "title_1": item1["title"],
                            "title_2": item2["title"],
                            "position_1": item1["pos"],
                            "position_2": item2["pos"],
                            "distance": distance
                        }
                        violations.append(violation_data)

        if violations:
            status = "FAIL"
            detail = f"Found {len(violations)} adjacent duplicate image(s)."
        else:
            status = "PASS"
            detail = "No adjacent duplicate images found."

        raw_data = {
            "violations": violations
        }

        return [ValidationResult(
            validator_name=self.name,
            status=status,
            detail=detail,
            raw_data=raw_data
        )]
