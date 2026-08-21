import random
from locust import task, between
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from users.base_user import BaseRecoUser
from utils.loader import (
    get_mmr_lambda, 
    get_similarity_threshold, 
    get_random_ip, 
    get_random_returning_client_id,
    get_article_scenarios
)

class ViralArticleUser(BaseRecoUser):
    """
    Simulates many users flooding a single specific article due to it being 'viral'.
    """
    wait_time = between(1, 2)
    
    def on_start(self):
        super().on_start()
        # We reuse returning users who are clicking on the viral article
        self.client_id = get_random_returning_client_id()
        self.ip_address = get_random_ip()
        
        # Select the first scenario as the "viral" article target
        scenarios = get_article_scenarios()
        self.viral_scenario = scenarios[0] if scenarios else {
            "item_id": "175149",
            "site": "padang",
            "article_title": "Viral News"
        }

    @task
    def visit_viral_article(self):
        params = {
            "item_id": self.viral_scenario.get("item_id"),
            "site": self.viral_scenario.get("site"),
            "article_title": self.viral_scenario.get("article_title", ""),
            "client_id": self.client_id,
            "ip_address": self.ip_address,
            "num_recommendation": 8,
            "recommendation_mode": "content-based",
            "type_recommendation": "recommend",
            "same_domain_only": "false",
            "freshness": 0.8,
            "localized": random.choice(["local", "global", "mix"]),
            "lambda_param": get_mmr_lambda(),
            "similarity_threshold": get_similarity_threshold()
        }
        
        with self.client.get(
            "/api/v3/article/recommendation", 
            params=params, 
            name="/api/v3/article/recommendation", 
            catch_response=True,
            timeout=15
        ) as response:
            self.validate_response(response, "Article Viral")
