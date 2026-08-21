from typing import List
from models import TestRequest, ValidationResult
from validators.base_validator import BaseValidator
import config

class LatencyValidator(BaseValidator):
    @property
    def name(self) -> str:
        return "Latency Validation"

    def validate(self, request: TestRequest) -> List[ValidationResult]:
        results = []
        
        # If API returned an error, don't validate latency (it's already failed in basic logic)
        if request.status_code == "ERROR" or request.latency_sec == "N/A":
            results.append(ValidationResult(self.name, "FAIL", "Latency cannot be measured due to API Error"))
            return results

        try:
            latency_ms = float(request.latency_sec) * 1000
        except ValueError:
            results.append(ValidationResult(self.name, "ERROR", f"Invalid latency value: {request.latency_sec}"))
            return results

        if latency_ms <= config.LATENCY_THRESHOLD_MS:
            results.append(ValidationResult(self.name, "PASS", f"Latency {latency_ms:.0f}ms is <= {config.LATENCY_THRESHOLD_MS}ms"))
        elif latency_ms <= config.LATENCY_TOLERANCE_MS:
            results.append(ValidationResult(self.name, "WARNING", f"Latency {latency_ms:.0f}ms is within tolerance ({config.LATENCY_THRESHOLD_MS}ms - {config.LATENCY_TOLERANCE_MS}ms)"))
        else:
            results.append(ValidationResult(self.name, "FAIL", f"Latency {latency_ms:.0f}ms exceeds threshold of {config.LATENCY_TOLERANCE_MS}ms"))

        return results
