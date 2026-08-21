from typing import List
from models import TestRequest, ValidationResult
from validators.base_validator import BaseValidator
import config

class ArticleRulesValidator(BaseValidator):
    @property
    def name(self) -> str:
        return "Article Rules Validation"

    def validate(self, request: TestRequest) -> List[ValidationResult]:
        results = []
        
        if request.endpoint != "/article":
            return results

        if not request.articles:
            results.append(ValidationResult(self.name, "FAIL", "No articles returned for article detail"))
            return results

        total = len(request.articles)
        similarity_count = sum(1 for a in request.articles if a.type == "similarity")
        top_news_count = sum(1 for a in request.articles if a.type == "top-news")

        if total != config.ARTICLE_TOTAL:
             results.append(ValidationResult(self.name, "FAIL", f"Total articles expected {config.ARTICLE_TOTAL}, but got {total}"))
        else:
             results.append(ValidationResult(self.name, "PASS", f"Total articles is {config.ARTICLE_TOTAL}"))

        comp_msg = ""
        if request.mode.lower() == "mix":
            comp_msg += f"PASS: Composition check skipped for mix mode. ({similarity_count} similarity, {top_news_count} top-news)\n"
            is_comp_valid = True
        else:
            if similarity_count != config.ARTICLE_SIMILARITY or top_news_count != config.ARTICLE_TOP_NEWS:
                 comp_msg += f"FAIL: Composition mismatch. Expected {config.ARTICLE_SIMILARITY} similarity & {config.ARTICLE_TOP_NEWS} top-news. Got {similarity_count} & {top_news_count}.\n"
                 is_comp_valid = False
            else:
                 comp_msg += f"PASS: Composition is correct ({similarity_count} similarity, {top_news_count} top-news)\n"
                 is_comp_valid = True

        comp_msg += "\nSimilarity Articles:\n"
        for a in request.articles:
            if a.type == "similarity":
                comp_msg += f"- ID: {a.id} | Title: \"{a.title}\" | {a.city}/{a.province}/{a.region}\n"
                
        comp_msg += "\nTop News Articles:\n"
        for a in request.articles:
            if a.type == "top-news":
                comp_msg += f"- ID: {a.id} | Title: \"{a.title}\" | {a.city}/{a.province}/{a.region}\n"

        if not is_comp_valid:
             results.append(ValidationResult(self.name, "FAIL", comp_msg))
        else:
             results.append(ValidationResult(self.name, "PASS", comp_msg))

        # Duplicate Detection
        seen_ids = set()
        duplicate_articles = []
        for a in request.articles:
            if a.id in seen_ids:
                duplicate_articles.append(a)
            else:
                seen_ids.add(a.id)

        if duplicate_articles:
            dup_msg = f"Found {len(duplicate_articles)} duplicate article(s) in response:\n"
            for dup in duplicate_articles:
                dup_msg += f"- ID: {dup.id} | Title: \"{dup.title}\"\n"
            results.append(ValidationResult(self.name, "FAIL", dup_msg))
        else:
            results.append(ValidationResult(self.name, "PASS", "No duplicate articles found"))

        return results
