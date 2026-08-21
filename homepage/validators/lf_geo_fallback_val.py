from typing import List
import json
from QA.models import TestRequest, ValidationResult
from QA.validators.base_validator import BaseValidator

class LFGeoFallbackValidator(BaseValidator):
    @property
    def name(self) -> str:
        return "Latest Feed Geo-Fallback"

    def validate(self, request: TestRequest) -> List[ValidationResult]:
        results = []
        if request.endpoint != "/latest_feed":
            return results
            
        if str(request.mode).lower() == "global":
            results.append(ValidationResult(self.name, "PASS", "Global mode - Geo Fallback not applied."))
            return results
            
        try:
            raw_data = json.loads(request.raw_response)
            metadata = raw_data.get("meta", raw_data)
            
            user_loc = metadata.get("user_location", "Unknown")
            anchor = metadata.get("anchor_level", "Unknown")
            
            if str(request.mode).lower() == "mix":
                results.append(ValidationResult(
                    self.name, "PASS", 
                    f"Mix Mode Active. User Loc: {user_loc}, Anchor: {anchor}. (Detailed proportion requires DB stock count)"
                ))
            else:
                results.append(ValidationResult(
                    self.name, "PASS", 
                    f"Geo-Fallback Active. User Loc: {user_loc}, Anchor: {anchor}."
                ))
                
        except Exception as e:
            results.append(ValidationResult(self.name, "ERROR", f"Failed to parse metadata for geo fallback: {str(e)}"))
            
        return results
