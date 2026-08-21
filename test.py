import requests
import csv
import json
import os
from datetime import datetime
import config

# 1. List of global IP addresses to test for BOTH endpoints
ip_addresses = [
#    ""
#   "140.213.138.238",
   "182.4.71.244",
#   "103.47.134.83",
#    "182.0.140.19",
#    "202.65.225.197",
#    "182.9.33.233",
#   "125.162.210.195",
#   "114.10.137.227", #(contradict maxmine)
#    "140.213.186.8", #(cotradict maxmine)
]

# 2. Endpoint URLs
URL_ARTICLE = "https://stg-reco-app.tribundata.com/api/v3/article/recommendation"
URL_HOMEPAGE = "https://stg-reco-app.tribundata.com/api/v3/homepage/recommendation"
URL_HEADER_TAG = getattr(config, 'HEADER_TAG_BASE_URL', "https://stg-reco-app.tribundata.com") + getattr(config, 'HEADER_TAG_ENDPOINT_PATH', "/api/v3/header/tag")

# 3. Configuration
HEADERS = {
    "accept": "application/json",
    "X-API-Key": config.API_KEY
}

def generate_client_ids():
    cfg = config.CLIENT_ID_CONFIG
    ids = []
    if cfg.get("mode") == "range":
        start = cfg.get("range_start", 1)
        end = cfg.get("range_end", 5)
        for i in range(start, end + 1):
            ids.append(f"test-{i:03d}")
    elif cfg.get("mode") == "list":
        ids = cfg.get("list", [])
    
    # Remove duplicates and sort
    return sorted(list(set(ids)))

def run_all_tests():
    # Setup Output Directory and Timestamp relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, config.OUTPUT_DIR)
    
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = os.path.join(output_dir, f"testing_{timestamp}.csv")

    client_ids = generate_client_ids()
    if not client_ids:
        print("No client IDs configured. Exiting.")
        return

    with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file, delimiter=';')

        writer.writerow([
            "Endpoint",
            "Scenario",
            "IP Address",
            "Client ID",
            "Mode",
            "Status Code",
            "Latency (Seconds)",
            "Model Code",
            "Articles Returned",
            "Returned Article IDs (Debug)",
            "Full Response / Error"
        ])

        total_article_scenarios = len(getattr(config, "ARTICLE_TEST_SCENARIOS", [{}]))
        print(f"Starting Matrix Tests: {len(client_ids)} Clients x {len(ip_addresses)} IPs = {len(client_ids) * len(ip_addresses)} combinations per scenario.\n")
        localized_modes = ["local", "global", "mix"]

        # ==========================================
        # TEST 1: ARTICLE RECOMMENDATION
        # ==========================================
        if getattr(config, "TEST_ARTICLE_ENDPOINT", True):
            print("--- Starting Test: Article Recommendation ---")
            scenarios = getattr(config, "ARTICLE_TEST_SCENARIOS", [{}])
            for scenario in scenarios:
                scenario_id = scenario.get("scenario_id", "SCN-DEFAULT")
                scenario_label = f"{scenario_id}: {scenario.get('scenario_name', 'Default')}"
                print(f"  >> Scenario: {scenario_label}")
                for client_id in client_ids:
                    for ip in ip_addresses:
                        for mode in localized_modes:
                            mode_label = mode.capitalize() if mode != "local" else "Localized"
                            params_article = {
                                "item_id": scenario.get("item_id", 1104407),
                                "site": scenario.get("site", "pekanbaru"),
                                "article_title": scenario.get("article_title", ""),
                                "client_id": client_id,
                                "ip_address": ip,
                                "num_recommendation": 8,
                                "recommendation_mode": "content-based",
                                "type_recommendation": "recommend",
                                "same_domain_only": "false",
                    #            "freshness": 0.8,
                                "localized": mode,
                                "lambda_param": config.MMR_LAMBDA,
                                "similarity_threshold": config.SIMILARITY_THRESHOLD
                            }

                            try:
                                response = requests.get(URL_ARTICLE, params=params_article, headers=HEADERS, timeout=15)
                                latency = response.elapsed.total_seconds()
                                status = response.status_code

                                if status == 200:
                                    data = response.json()
                                    api_data = data.get("data", data)
                                    if isinstance(api_data, list):
                                        model_code = data.get("model_code", "N/A")
                                        recommended_articles = api_data
                                    elif isinstance(api_data, dict):
                                        model_code = api_data.get("model_code", data.get("model_code", "N/A"))
                                        recommended_articles = api_data.get("recommended_article", data.get("recommended_article", []))
                                    else:
                                        model_code = "N/A"
                                        recommended_articles = []
                                    num_returned = len(recommended_articles)
                                    article_ids = [str(item.get("id")) for item in recommended_articles]
                                    id_string = ", ".join(article_ids)
                                    raw_response = json.dumps(data)
                                else:
                                    model_code, num_returned, id_string = "N/A", 0, "N/A"
                                    raw_response = response.text

                                writer.writerow(["/article", scenario_label, ip, client_id, mode_label, status, latency, model_code, num_returned, id_string, raw_response])
                                print(f"[{scenario_id} - Article - {mode_label:<9}] User: {client_id} | IP: {ip:<15} | IDs: [{id_string}]")

                            except requests.exceptions.RequestException as e:
                                writer.writerow(["/article", scenario_label, ip, client_id, mode_label, "ERROR", "N/A", "N/A", "N/A", "N/A", str(e)])
                                print(f"[{scenario_id} - Article FAILED] User: {client_id} | IP: {ip:<15} | Error: {e}")
        else:
            print("--- Skipping Test: Article Recommendation ---")

        # ==========================================
        # TEST 2: HOMEPAGE RECOMMENDATION
        # ==========================================
        if getattr(config, "TEST_HOMEPAGE_ENDPOINT", True):
            print("\n--- Starting Test: Homepage Recommendation ---")
            for client_id in client_ids:
                for ip in ip_addresses:
                    for mode in localized_modes:
                        mode_label = mode.capitalize() if mode != "local" else "Localized"
                        params_homepage = {
                            "client_id": client_id,
                            "ip_address": ip,
                            "num_recommendation": 20,
                            "page_mode": "homepage",
                            "localized": mode,
                            # Added config parameters
                            "lambda_param": config.MMR_LAMBDA,
                            "similarity_threshold": config.SIMILARITY_THRESHOLD
                        }

                        try:
                            response = requests.get(URL_HOMEPAGE, params=params_homepage, headers=HEADERS, timeout=15)
                            latency = response.elapsed.total_seconds()
                            status = response.status_code

                            if status == 200:
                                res_json = response.json()
                                api_data = res_json.get("data", [])
                                if isinstance(api_data, dict):
                                    model_code = api_data.get("model_code", "N/A")
                                    recommended_articles = api_data.get("recommended_article", [])
                                else:
                                    model_code = "N/A"
                                    recommended_articles = api_data
                                num_returned = len(recommended_articles)
                                article_ids = [str(item.get("id")) for item in recommended_articles]
                                id_string = ", ".join(article_ids)
                                raw_response = json.dumps(res_json)
                            else:
                                model_code, num_returned, id_string = "N/A", 0, "N/A"
                                raw_response = response.text

                            writer.writerow(["/homepage", "Homepage Default", ip, client_id, mode_label, status, latency, model_code, num_returned, id_string, raw_response])
                            print(f"[Homepage - {mode_label:<9}] User: {client_id} | IP: {ip:<15} | IDs: [{id_string[:50]}...]")

                        except requests.exceptions.RequestException as e:
                            writer.writerow(["/homepage", "Homepage Default", ip, client_id, mode_label, "ERROR", "N/A", "N/A", "N/A", "N/A", str(e)])
                            print(f"[Homepage FAILED] User: {client_id} | IP: {ip:<15} | Mode: {mode_label} | Error: {e}")
        else:
            print("\n--- Skipping Test: Homepage Recommendation ---")


    print(f"\nAll tests complete. Check '{csv_filename}' for details.")

if __name__ == "__main__":
    run_all_tests()