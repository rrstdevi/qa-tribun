from typing import List
import re
from models import TestRequest, ValidationResult
from validators.base_validator import BaseValidator
import config

class HomepageRulesValidator(BaseValidator):
    @property
    def name(self) -> str:
        return "Homepage Rules Validation"

    def validate(self, request: TestRequest) -> List[ValidationResult]:
        results = []
        
        if request.endpoint != "/homepage":
            return results

        if not request.articles:
            results.append(ValidationResult(self.name, "FAIL", "No articles returned for homepage"))
            return results

        total = len(request.articles)
        personalized_count = sum(1 for a in request.articles if a.type == "personalized")
        top_news_count = sum(1 for a in request.articles if a.type == "top-news")

        # 1. Total Count Check
        expected_total = 40 if request.mode.lower() == "mix" else config.HOMEPAGE_MAX_ARTICLES
        if total == expected_total:
            msg = f"Returned exactly {expected_total} articles ({personalized_count} personalized, {top_news_count} top-news)"
            results.append(ValidationResult(self.name, "PASS", msg))
        else:
            msg = f"Returned {total} articles, expected exactly {expected_total} ({personalized_count} personalized, {top_news_count} top-news)"
            results.append(ValidationResult(self.name, "FAIL", msg))

        # 2. Blacklist Check
        blacklist_pattern = re.compile(config.BLACKLIST_REGEX_PATTERN)
        blacklist_failures = []
        for a in request.articles:
            if blacklist_pattern.search(a.title):
                blacklist_failures.append(a.id)
                
        if blacklist_failures:
            results.append(ValidationResult(self.name, "FAIL", f"Blacklist detected in article IDs: {blacklist_failures}"))
        else:
            results.append(ValidationResult(self.name, "PASS", "No blacklisted keywords found in titles"))

        # 3. Duplicate Detection
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
