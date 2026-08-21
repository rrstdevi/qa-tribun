import sys
import os
import random
import uuid

# Append parent directory to sys.path so we can import 'config.py'
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if root_dir not in sys.path:
    sys.path.append(root_dir)

import config

def get_api_key():
    return getattr(config, "API_KEY", "")

def get_mmr_lambda():
    return getattr(config, "MMR_LAMBDA", 0.7)

def get_similarity_threshold():
    return getattr(config, "SIMILARITY_THRESHOLD", 60.0)

def get_ip_addresses():
    # Sourced from test.py
    return [
        "182.4.71.244",
        "103.47.134.83",
        "182.0.140.19",
        "202.65.225.197",
        "182.9.33.233",
        "125.162.210.195",
        "114.10.137.227",
        "140.213.186.8"
    ]

def get_article_scenarios():
    return getattr(config, "ARTICLE_TEST_SCENARIOS", [
        {
            "scenario_id": "SCN-001",
            "item_id": "175149",
            "site": "padang"
        }
    ])

def get_client_ids():
    cfg = getattr(config, "CLIENT_ID_CONFIG", {})
    ids = []
    if cfg.get("mode") == "range":
        start = cfg.get("range_start", 1)
        end = cfg.get("range_end", 100)
        for i in range(start, end + 1):
            ids.append(f"test-{i:03d}")
    elif cfg.get("mode") == "list":
        ids = cfg.get("list", [])
        
    if not ids:
        ids = [f"test-mock-{i}" for i in range(10)]
    return sorted(list(set(ids)))

def get_random_ip():
    return random.choice(get_ip_addresses())

def get_random_cold_start_client_id():
    """Generates a fresh UUID client_id for cold start user"""
    return f"locust-cs-{uuid.uuid4().hex[:8]}"

def get_random_returning_client_id():
    """Gets a predefined client_id from config for returning user"""
    return random.choice(get_client_ids())
