from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class Article:
    id: int
    title: str
    publish_date: str
    region: str
    city: str
    province: str
    type: str
    site: Optional[str] = None
    section_title: Optional[str] = None
    _feed_source: Optional[bool] = None
    raw_json: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TestRequest:
    row_num: int
    endpoint: str
    scenario: str
    ip_address: str
    client_id: str
    mode: str
    status_code: str
    latency_sec: float
    model_code: str
    articles: List[Article] = field(default_factory=list)
    raw_response: str = ""
    execution_time_ms: float = 0.0

@dataclass
class ValidationResult:
    validator_name: str
    status: str  # "PASS", "FAIL", "WARNING", "ERROR"
    detail: str
    raw_data: Dict[str, Any] = field(default_factory=dict)
