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
    get_random_cold_start_client_id
)

class ColdStartUser(BaseRecoUser):
    """
    Simulates a brand new user. 
    They have a fresh client_id which has never interacted with the system before.
    They only visit the homepage.
    """
    wait_time = between(1, 3)
    
    def on_start(self):
        super().on_start()
        # Fresh identity simulating first open
        self.client_id = get_random_cold_start_client_id()
        self.ip_address = get_random_ip()

    @task
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
            self.validate_response(response, "Homepage Cold Start")
