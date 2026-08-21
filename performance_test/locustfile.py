import os
import sys
from locust import events
try:
    from dotenv import load_dotenv
    # Try to load .env.dev from the root directory if it exists, matching the old script's behavior
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.dev"))
except ImportError:
    pass

# Adjust path so locust can be run from the root or performance_test folder
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from users.returning_user import ReturningUser
from users.cold_start_user import ColdStartUser
from users.viral_user import ViralArticleUser

@events.init_command_line_parser.add_listener
def _(parser):
    parser.add_argument(
        "--scenario",
        type=str,
        env_var="LOCUST_SCENARIO",
        default="normal",
        help="Test scenario to run. Options: normal, homepage_load, viral, cold_start, returning_user"
    )
    # Allows setting host cleanly if not passed via web UI
    parser.add_argument(
        "--host-url", 
        type=str, 
        env_var="LOCUST_HOST", 
        default="https://stg-reco-app.tribundata.com", 
        help="Base URL of the target system"
    )

@events.init.add_listener
def on_locust_init(environment, **kwargs):
    scenario = environment.parsed_options.scenario
    
    # Check if host is set in options, else use the default
    if not environment.host and environment.parsed_options.host_url:
        environment.host = environment.parsed_options.host_url
    
    # We assign exactly what we want based on scenario
    environment.user_classes = []
    
    if scenario == "normal":
        # 70% returning users, 30% cold start users
        ReturningUser.weight = 7
        ColdStartUser.weight = 3
        environment.user_classes = [ReturningUser, ColdStartUser]
        print("--> Starting Locust Scenario: Normal Traffic (70% Returning, 30% Cold Start)")
        
    elif scenario == "homepage_load":
        # ColdStartUser only hits homepage, so we can use them for pure homepage load
        ColdStartUser.weight = 1
        environment.user_classes = [ColdStartUser]
        print("--> Starting Locust Scenario: Homepage Load Test (100% Homepage API calls)")
        
    elif scenario == "viral":
        ViralArticleUser.weight = 1
        environment.user_classes = [ViralArticleUser]
        print("--> Starting Locust Scenario: Viral Article Traffic (100% Article API calls for specific item)")
        
    elif scenario == "cold_start":
        ColdStartUser.weight = 1
        environment.user_classes = [ColdStartUser]
        print("--> Starting Locust Scenario: Cold Start Load Test (100% New Users)")
        
    elif scenario == "returning_user":
        ReturningUser.weight = 1
        environment.user_classes = [ReturningUser]
        print("--> Starting Locust Scenario: Returning User Personalization (100% Returning Users)")
        
    else:
        print(f"Unknown scenario: {scenario}. Falling back to normal.")
        ReturningUser.weight = 7
        ColdStartUser.weight = 3
        environment.user_classes = [ReturningUser, ColdStartUser]
