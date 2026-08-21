from typing import List, Dict
from models import TestRequest, ValidationResult
from validators.base_validator import BaseCrossValidator

class ColdStartValidator(BaseCrossValidator):
    @property
    def name(self) -> str:
        return "Cold Start Validation"

    def validate_all(self, requests: List[TestRequest], context: Dict[TestRequest, List[ValidationResult]]):
        # Group requests by endpoint and client_id
        # We only care about /homepage for cold start (since /article has a different composition logic usually, 
        # but the prompt implies this is for personalization. The prompt mentioned "5 article top-news 3 article personalized" which is /homepage context.)
        # Wait, the prompt says "seluruh recommendation masih berupa TOP NEWS". This applies to /homepage.
        
        # Group by (client_id, ip_address) -> {"localized": req, "global": req}
        client_map = {}
        for req in requests:
            if "homepage" in req.endpoint.lower():
                key = (req.client_id, req.ip_address)
                if key not in client_map:
                    client_map[key] = {}
                mode = req.mode.lower()
                client_map[key][mode] = req

        for key_tuple, req_group in client_map.items():
            client_id = key_tuple[0]
            
            # Process mix mode
            mix_req = req_group.get("mix")
            if mix_req:
                mix_results = context.get(mix_req.row_num, [])
                mix_target_res = next(
                    (r for r in mix_results if r.validator_name == "Localization Validation"), 
                    None
                )
                
                mix_local_articles = [a for a in mix_req.articles if getattr(a, "_feed_source", False) is True]
                mix_personalized_local = [a for a in mix_local_articles if a.type == "personalized"]
                
                mix_global_articles = [a for a in mix_req.articles if getattr(a, "_feed_source", False) is False]
                mix_personalized_global = [a for a in mix_global_articles if a.type == "personalized"]
                
                is_mix_cold_start = not mix_personalized_local and not mix_personalized_global
                
                if is_mix_cold_start:
                    if mix_target_res and mix_target_res.status == "FAIL":
                        mix_target_res.status = "PASS"
                        mix_target_res.detail = "[OVERRIDDEN BY COLD START VALIDATOR]\n" + mix_target_res.detail
                        
                    detail_msg = (
                        f"Client ID: {client_id}\n\n"
                        "Mix Mode:\n"
                        "- Article Types: ALL TOP-NEWS\n"
                        "- Cold Start Detection: TRUE\n\n"
                        "Final Result:\nPASS (Cold Start User)"
                    )
                    context[mix_req.row_num].append(ValidationResult(self.name, "COLD START USER", detail_msg))
                else:
                    if mix_target_res and (mix_target_res.status == "FAIL" or mix_target_res.raw_data.get("overridden_to_pass") == True):
                        if mix_target_res.status != "PASS":
                            detail_msg = "Final Result:\nFAIL\n\nReason:\nMix mode localization inconsistency detected but personalized article still exists."
                            if mix_personalized_local:
                                p_ids = [str(a.id) for a in mix_personalized_local]
                                detail_msg += f"\n- Local portion has personalized articles: {', '.join(p_ids)}"
                            if mix_personalized_global:
                                p_ids = [str(a.id) for a in mix_personalized_global]
                                detail_msg += f"\n- Global portion has personalized articles: {', '.join(p_ids)}"
                                
                            context[mix_req.row_num].append(ValidationResult(self.name, "FAIL", detail_msg))

            loc_req = req_group.get("localized")
            glob_req = req_group.get("global")

            if not loc_req:
                continue

            # 1. Get Localization Validation result
            loc_results = context.get(loc_req.row_num, [])
            target_res = next(
                (r for r in loc_results if r.validator_name == "Localization Validation"), 
                None
            )

            # 2. Check if all articles in Localized mode are 'top-news'
            loc_personalized_articles = [a for a in loc_req.articles if a.type == "personalized"]
            
            # 3. Check Global mode
            glob_personalized_articles = []
            if glob_req:
                glob_personalized_articles = [a for a in glob_req.articles if a.type == "personalized"]

            # Evaluate Final Rules
            is_cold_start = not loc_personalized_articles and (not glob_req or not glob_personalized_articles)

            if is_cold_start:
                # Condition PASS: All top-news in both modes
                
                # If localization failed, override its status to PASS
                if target_res and target_res.status == "FAIL":
                    target_res.status = "PASS"
                    target_res.detail = "[OVERRIDDEN BY COLD START VALIDATOR]\n" + target_res.detail

                detail_msg = (
                    f"Client ID: {client_id}\n\n"
                    "Localized Mode:\n"
                    "- Article Types: ALL TOP-NEWS\n"
                    "- Cold Start Detection: TRUE\n\n"
                )
                if glob_req:
                    detail_msg += (
                        "Global Mode:\n"
                        "- Article Types: ALL TOP-NEWS\n"
                        "- Cold Start Detection: TRUE\n\n"
                    )
                else:
                    detail_msg += "Global Mode: Not found for cross-validation.\n\n"

                detail_msg += "Final Result:\nPASS (Cold Start User)"
                
                context[loc_req.row_num].append(ValidationResult(self.name, "COLD START USER", detail_msg))

            else:
                # NOT a cold start user
                # Only check if localization was FAIL or overridden_to_pass to raise inconsistency
                if target_res and (target_res.status == "FAIL" or target_res.raw_data.get("overridden_to_pass") == True):
                    # If localization was overridden to PASS (due to missing IP), it's not an inconsistency.
                    # Since there are personalized articles, it's not a cold start user.
                    # So we just skip it to avoid false FAIL.
                    if target_res.status == "PASS":
                        continue

                    # Condition FAIL: Localized failed inconsistency BUT there is a personalized article
                    detail_msg = "Final Result:\nFAIL\n\nReason:\nLocalized inconsistency detected but personalized article still exists."
                    
                    if loc_personalized_articles:
                        p_ids = [str(a.id) for a in loc_personalized_articles]
                        detail_msg += f"\n- Localized mode has personalized articles: {', '.join(p_ids)}"
                    
                    if glob_personalized_articles:
                        p_ids = [str(a.id) for a in glob_personalized_articles]
                        detail_msg += f"\n- Global mode has personalized articles: {', '.join(p_ids)}"
                        
                    context[loc_req.row_num].append(ValidationResult(self.name, "FAIL", detail_msg))
                else:
                    # Localization PASSed normally, and user is NOT a cold start.
                    # We just skip as expected.
                    continue
