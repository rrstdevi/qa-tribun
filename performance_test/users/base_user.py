import json
from locust import HttpUser
import sys
import os

# Ensure utils can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.loader import get_api_key

class BaseRecoUser(HttpUser):
    abstract = True  # Tell locust not to instantiate this directly

    def on_start(self):
        """
        Initialization for all users.
        Sets up default headers.
        """
        api_key = get_api_key()
        self.client.headers.update({
            "accept": "application/json",
            "X-API-Key": api_key
        })
        self.ip_address = None
        self.client_id = None
        
    def validate_response(self, response, endpoint_name):
        """
        Sanity validation for all requests.
        Ensures HTTP 200 and valid JSON with data.
        """
        if response.status_code == 0:
            # Locust might return 0 for timeouts or connection errors
            response.failure(f"[{endpoint_name}] Connection Error or Timeout")
            return False

        if response.status_code != 200:
            response.failure(f"[{endpoint_name}] HTTP {response.status_code}")
            return False
            
        try:
            data = response.json()
            api_data = data.get("data", [])
            
            # Extract list of articles based on current API structure
            if isinstance(api_data, dict):
                recommended_articles = api_data.get("recommended_article", [])
            else:
                recommended_articles = api_data
                
            if not recommended_articles or len(recommended_articles) == 0:
                response.failure(f"[{endpoint_name}] Empty recommendations returned")
                return False
                
            return True
        except json.JSONDecodeError:
            response.failure(f"[{endpoint_name}] Invalid JSON Response")
            return False
