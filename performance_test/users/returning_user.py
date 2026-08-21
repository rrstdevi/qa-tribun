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

class ReturningUser(BaseRecoUser):
    """
    Simulates a returning user who has a persistent client_id and IP across their session.
    They mostly browse the homepage, but occasionally read articles.
    """
    wait_time = between(1, 3)
    
    def on_start(self):
        super().on_start()
        # Identity persists for the lifecycle of this virtual user
        self.client_id = get_random_returning_client_id()
        self.ip_address = get_random_ip()
        self.scenarios = get_article_scenarios()

    @task(7)
    def visit_homepage(self):
        params = {
            "client_id": self.client_id,
            "ip_address": self.ip_address,
            "num_recommendation": 20,
            "page_mode": "homepage",
            "localized": random.choice(["local", "global", "mix"]),
            "lambda_param": get_mmr_lambda(),
            "similarity_threshold": get_similarity_threshold()
        }
        
        with self.client.get(
            "/api/v3/homepage/recommendation", 
            params=params, 
            name="/api/v3/homepage/recommendation", 
            catch_response=True,
            timeout=15
        ) as response:
            self.validate_response(response, "Homepage Returning User")

    @task(3)
    def visit_article(self):
        scenario = random.choice(self.scenarios)
        params = {
            "item_id": scenario.get("item_id", "175149"),
            "site": scenario.get("site", "padang"),
            "article_title": scenario.get("article_title", ""),
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
            self.validate_response(response, "Article Returning User")
