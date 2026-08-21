import re
import unicodedata
import itertools
from typing import List, Dict, Any
from rapidfuzz import fuzz
from models import TestRequest, ValidationResult
from validators.base_validator import BaseValidator
import config

class SimilarityValidator(BaseValidator):
    """
    Production-grade Similarity Validator menggunakan RapidFuzz.
    Menerapkan Strict Zero Tolerance berbasis fuzz.WRatio.
    Merekam seluruh hasil uji (violations dan safe_pairs) untuk observability MMR.
    """
    @property
    def name(self) -> str:
        return "Similarity Validation (RapidFuzz)"

    def _normalize_text(self, text: str) -> str:
        """
        Normalisasi layer untuk fuzzy matching yang akurat.
        Meliputi lowercase, hapus tanda baca, trim whitespace, dan Unicode NFKD.
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
        if not request.articles or request.endpoint != "/homepage":
            return []

        # 1. Cached Preprocessing (Normalisasi SATU KALI di awal untuk performa)
        cached_titles: Dict[int, str] = {}
        for article in request.articles:
            cached_titles[article.id] = self._normalize_text(article.title)

        warnings: List[Dict[str, Any]] = []
        violations: List[Dict[str, Any]] = []
        
        threshold = getattr(config, "SIMILARITY_THRESHOLD", 60.0)
        anomaly_gap = getattr(config, "SIMILARITY_ANOMALY_GAP", 25.0)
        max_ratio = 0.0
        total_ratio = 0.0
        total_pairs = 0

        # Helper Function untuk menghitung kemiripan dan merekam data
        def process_pair(type_name: str, id_1: int, title_1: str, norm_1: str, id_2: int, title_2: str, norm_2: str):
            nonlocal max_ratio, total_ratio, total_pairs
            
            # Source of Truth
            ratio_score = fuzz.ratio(norm_1, norm_2)
            
            # Observability Scorers
            token_sort_score = fuzz.token_sort_ratio(norm_1, norm_2)
            token_set_score = fuzz.token_set_ratio(norm_1, norm_2)
            
            # Aggregation Metrics Update
            max_ratio = max(max_ratio, ratio_score)
            total_ratio += ratio_score
            total_pairs += 1
            
            gap_sort = abs(ratio_score - token_sort_score)
            gap_set = abs(ratio_score - token_set_score)
            
            pair_data = {
                "type": type_name,
                "article_1_id": id_1,
                "article_1_title_raw": title_1,
                "article_2_id": id_2,
                "article_2_title_raw": title_2,
                "ratio_score": round(ratio_score, 2),
                "token_sort_score": round(token_sort_score, 2),
                "token_set_score": round(token_set_score, 2),
                "gap_sort": round(gap_sort, 2),
                "gap_set": round(gap_set, 2)
            }
            
            # Decision Rule
            if gap_sort >= anomaly_gap or gap_set >= anomaly_gap:
                max_obs = max(token_sort_score, token_set_score)
                if max_obs > ratio_score:
                    pair_data["warning_message"] = "Token Similarity Tinggi, Namun Ratio Rendah"
                else:
                    pair_data["warning_message"] = "Ratio Tinggi, Namun Token Similarity Rendah"
                warnings.append(pair_data)
            elif ratio_score >= threshold:
                violations.append(pair_data)

        # 2. Cross-Similarity Check (Pairwise Combinations)
        # Menghindari O(N^2) preprocessing dengan memanfaatkan cached_titles
        for art_1, art_2 in itertools.combinations(request.articles, 2):
            process_pair(
                "cross-similarity",
                art_1.id, art_1.title, cached_titles[art_1.id],
                art_2.id, art_2.title, cached_titles[art_2.id]
            )

        # 3. Pack Output Metrics
        avg_ratio = (total_ratio / total_pairs) if total_pairs > 0 else 0.0
        
        metrics = {
            "average_ratio": round(avg_ratio, 2),
            "max_ratio": round(max_ratio, 2),
            "warning_count": len(warnings),
            "violation_count": len(violations),
            "total_pairs_checked": total_pairs,
            "threshold_used": threshold,
            "anomaly_gap_used": anomaly_gap
        }
        
        raw_data = {
            "metrics": metrics,
            "warnings": warnings,
            "violations": violations
        }

        # 4. Final Status Determination
        if warnings:
            status = "WARNING"
        elif violations:
            status = "FAIL"
        else:
            status = "PASS"
            
        detail_msg = "Detail tersedia di HTML Report."

        return [ValidationResult(
            validator_name=self.name,
            status=status,
            detail=detail_msg,
            raw_data=raw_data
        )]
