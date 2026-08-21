from typing import List, Dict
from models import TestRequest, ValidationResult
from validators.base_validator import BaseCrossValidator

class LocalGlobalDuplicateValidator(BaseCrossValidator):
    @property
    def name(self) -> str:
        return "Local vs Global Duplicate Validation"

    def validate_all(self, requests: List[TestRequest], context: Dict[int, List[ValidationResult]]):
        # Group by (endpoint, client_id, ip_address, scenario) -> {"localized": req, "global": req}
        client_map = {}
        for req in requests:
            key = (req.endpoint.lower(), req.client_id, req.ip_address, req.scenario)
            if key not in client_map:
                client_map[key] = {}
            mode = req.mode.lower()
            client_map[key][mode] = req

        for key_tuple, req_group in client_map.items():
            # 1. Process mix mode internal duplicate check
            mix_req = req_group.get("mix")
            if mix_req and mix_req.articles:
                loc_mix_articles = {a.id: a for a in mix_req.articles if getattr(a, "_feed_source", False) is True and a.id}
                glob_mix_articles = [a for a in mix_req.articles if getattr(a, "_feed_source", False) is False]
                
                mix_duplicates = []
                for a in glob_mix_articles:
                    if a.id in loc_mix_articles:
                        loc_a = loc_mix_articles[a.id]
                        mix_duplicates.append({
                            "loc_id": loc_a.id,
                            "loc_title": loc_a.title,
                            "glob_id": a.id,
                            "glob_title": a.title
                        })
                
                if len(mix_duplicates) > 0:
                    detail_msg = f"Found {len(mix_duplicates)} duplicate article(s) internally between Local and Global within Mix mode.\n\n"
                    detail_msg += "Duplicates:\n"
                    for d in mix_duplicates:
                        detail_msg += f"- lokal : {d['loc_id']}, {d['loc_title']} & global : {d['glob_id']}, {d['glob_title']}\n"
                    context[mix_req.row_num].append(ValidationResult(self.name, "FAIL", detail_msg))
                else:
                    detail_msg = "No duplicate articles found between Local and Global within Mix mode.\n"
                    context[mix_req.row_num].append(ValidationResult(self.name, "PASS", detail_msg))

            # 2. Process localized vs global duplicate check
            loc_req = req_group.get("localized")
            glob_req = req_group.get("global")

            if not loc_req or not glob_req:
                continue

            # Skip if any of them had an error or empty articles
            if not loc_req.articles or not glob_req.articles:
                continue

            # Extract localized articles
            loc_articles_map = {a.id: a for a in loc_req.articles if a.id}
            
            duplicates = []
            for a in glob_req.articles:
                if a.id in loc_articles_map:
                    loc_a = loc_articles_map[a.id]
                    duplicates.append({
                        "loc_id": loc_a.id,
                        "loc_title": loc_a.title,
                        "glob_id": a.id,
                        "glob_title": a.title
                    })

            # Check if there are duplicates
            if len(duplicates) > 0:
                detail_msg = f"Found {len(duplicates)} duplicate article(s) between Localized and Global mode.\n\n"
                detail_msg += "Duplicates:\n"
                for d in duplicates:
                    detail_msg += f"- lokal : {d['loc_id']}, {d['loc_title']} & global : {d['glob_id']}, {d['glob_title']}\n"
                
                context[loc_req.row_num].append(ValidationResult(self.name, "FAIL", detail_msg))
                context[glob_req.row_num].append(ValidationResult(self.name, "FAIL", detail_msg))
            else:
                detail_msg = "No duplicate articles found between Localized and Global mode.\n"
                context[loc_req.row_num].append(ValidationResult(self.name, "PASS", detail_msg))
                context[glob_req.row_num].append(ValidationResult(self.name, "PASS", detail_msg))
