from typing import List, Dict, Tuple
import data_loader
from models import TestRequest, ValidationResult, Article
from validators.base_validator import BaseValidator
from utils.location_utils import normalize_location_name

class LocalizationValidator(BaseValidator):
    @property
    def name(self) -> str:
        return "Localization Validation"

    def get_hierarchical_anchor(self, articles: List[Article]) -> Tuple[str, str, Dict[str, float]]:
        """
        Determines the anchor level (city, province, region) based on majority consistency.
        Only evaluates 'personalized' articles if available.
        Returns: (anchor_level, anchor_value, consistency_stats)
        """
        # 1. Filter personalized articles
        target_articles = [a for a in articles if a.type == "personalized"]
        if not target_articles:
            # Fallback if no personalized articles exist (handled by Cold Start later, but we still need an anchor)
            target_articles = articles
            
        if not target_articles:
            return None, None, {}

        total = len(target_articles)
        stats = {}
        
        # Calculate consistency for each level
        for level in ['city', 'province', 'region']:
            counts = {}
            for a in target_articles:
                val = normalize_location_name(getattr(a, level, ""))
                if val:
                    counts[val] = counts.get(val, 0) + 1
                    
            if counts:
                max_val = max(counts, key=counts.get)
                max_count = counts[max_val]
                percentage = (max_count / total) * 100
                stats[level] = {
                    "value": max_val,
                    "percentage": percentage
                }
            else:
                stats[level] = {"value": None, "percentage": 0.0}

        # 2. Select Anchor (Find highest consistency >= 50%, tie-break: City > Province > Region)
        anchor_level = None
        anchor_value = None
        max_perc = 0.0
        
        for level in ['city', 'province', 'region']:
            perc = stats[level]["percentage"]
            if perc >= 50 and perc > max_perc:
                max_perc = perc
                anchor_level = level
                anchor_value = stats[level]["value"]
                
        return anchor_level, anchor_value, stats

    def validate(self, request: TestRequest) -> List[ValidationResult]:
        results = []
        
        if request.mode.lower() not in ("localized", "mix"):
            return results

        if not request.articles:
            return results

        if request.mode.lower() == "mix":
            target_articles = [a for a in request.articles if getattr(a, "_feed_source", False) is True]
            if not target_articles:
                return results
        else:
            target_articles = request.articles

        anchor_level, anchor_value, stats = self.get_hierarchical_anchor(target_articles)

        detail_msg = "Localization Validation:\n"

        ranked_levels = []
        if anchor_level:
            hierarchy = ['city', 'province', 'region']
            start_idx = hierarchy.index(anchor_level)
            ranked_levels = [lvl for lvl in hierarchy[start_idx:] if stats.get(lvl, {}).get('value')]

        detail_msg += "Anchor Fallback Ranking:\n"
        if not anchor_level:
            detail_msg += "Selected Anchor Level: NONE\n"
            detail_msg += "Reason: No hierarchy reached minimum consistency threshold (>50%).\n\n"
        elif not ranked_levels:
            detail_msg += "No valid location fields found in articles to form a fallback sequence.\n\n"
        else:
            detail_msg += f"Main Anchor: {anchor_level.capitalize()} (>50%)\n"
            for rank, level in enumerate(ranked_levels, 1):
                val = stats[level]['value']
                perc = stats[level]['percentage']
                detail_msg += f"{rank}. {level.capitalize()} = {val} ({perc:.1f}%)\n"
            detail_msg += "\n"

        # 1. Dataset Supporting Validation & Override Rule
        ip_mapping = data_loader.load_ip_mapping()
        ip_data = ip_mapping.get(request.ip_address)
        
        is_ip_unavailable = False
        if not ip_data:
            is_ip_unavailable = True
        else:
            c = normalize_location_name(ip_data.get('city'))
            p = normalize_location_name(ip_data.get('province'))
            r = normalize_location_name(ip_data.get('region'))
            if not c and not p and not r:
                is_ip_unavailable = True

        raw_meta = {}
        
        if is_ip_unavailable:
            detail_msg += "Dataset Validation:\nResult: SKIPPED (IP location data is unavailable)\n\n"
            detail_msg += "Final Result:\nPASS\n\n"
            detail_msg += "[OVERRIDE] Localization validation set to PASS because baseline location data (IP or Anchor) is unavailable.\n"
            raw_meta = {"overridden_to_pass": True, "reason": "missing_location_data"}
            results.append(ValidationResult(self.name, "PASS", detail_msg, raw_data=raw_meta))
            return results

        dataset_status = "FAIL"
        winning_anchor_level = None
        winning_anchor_value = None
        
        detail_msg += "Dataset Validation:\n"
        
        if not ranked_levels:
            detail_msg += "Result: FAIL (No valid anchor levels to compare)\n\n"
        else:
            for level in ranked_levels:
                anchor_val = stats[level]['value']
                ds_val = normalize_location_name(ip_data.get(level))
                
                detail_msg += f"- Checking {level.capitalize()}:\n"
                detail_msg += f"  Anchor: {anchor_val} | Dataset: {ds_val or 'NULL'}\n"
                
                if not ds_val:
                    detail_msg += "  Status: SKIPPED (Dataset field empty, falling back...)\n"
                    continue
                    
                if ds_val == anchor_val:
                    detail_msg += "  Status: MATCH\n"
                    dataset_status = "PASS"
                    winning_anchor_level = level
                    winning_anchor_value = anchor_val
                    break
                else:
                    detail_msg += "  Status: MISMATCH (Falling back if available...)\n"
                    
            if dataset_status == "PASS":
                detail_msg += f"\nWinning Anchor: {winning_anchor_level.capitalize()} ({winning_anchor_value})\n"
                detail_msg += "Result: PASS\n\n"
            else:
                detail_msg += "\nResult: FAIL (All available levels mismatched or missing in dataset)\n\n"

        # 2. Articles Validation vs Anchor
        mismatches = []
        has_fail = False
        
        import json
        for a in target_articles:
            if not winning_anchor_level:
                check_level = ranked_levels[0] if ranked_levels else None
                check_val = stats[check_level]['value'] if check_level else None
            else:
                check_level = winning_anchor_level
                check_val = winning_anchor_value
                
            if not check_level:
                is_mismatch = True
            else:
                norm_val = normalize_location_name(getattr(a, check_level, ""))
                is_mismatch = (norm_val != check_val)
                
            if is_mismatch:
                if not check_level:
                    item_msg = f"- Article ID {a.id}\n  City: {a.city} | Prov: {a.province} | Region: {a.region}\n  Type: {a.type}\n"
                else:
                    norm_val = normalize_location_name(getattr(a, check_level, ""))
                    item_msg = f"- Article ID {a.id}\n  {check_level.capitalize()}: {norm_val}\n  Type: {a.type}\n"
                
                # Apply Backfill Rule
                if a.type == "top-news":
                    item_msg += "  Result: PASS (BACKFILL DETECTED)\n"
                else:
                    item_msg += "  Result: FAIL (NOT DETECTED)\n"
                    has_fail = True
                
                raw_json_str = json.dumps(a.raw_json, indent=2)
                item_msg += f"  Raw JSON:\n{raw_json_str}\n"
                    
                mismatches.append(item_msg)

        if mismatches:
            detail_msg += "Mismatch Articles:\n" + "\n".join(mismatches)
        else:
            detail_msg += "Mismatch Articles: None\n"

        # Determine Final Status
        final_status = "PASS"
        if dataset_status == "FAIL" or has_fail or not ranked_levels:
            final_status = "FAIL"

        results.append(ValidationResult(self.name, final_status, detail_msg, raw_data=raw_meta))
        return results
