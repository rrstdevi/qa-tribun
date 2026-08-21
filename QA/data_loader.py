import csv
import json
import os
from typing import List, Dict
from models import TestRequest, Article
import config

IP_MAPPING_CACHE = None

def load_ip_mapping() -> Dict[str, dict]:
    global IP_MAPPING_CACHE
    if IP_MAPPING_CACHE is not None:
        return IP_MAPPING_CACHE
        
    mapping = {}
    try:
        # Resolve path relative to Data Product root
        script_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.abspath(os.path.join(script_dir, '..'))
        ip_path = os.path.join(root_dir, config.IP_DATA_CSV_PATH)
        with open(ip_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ip = row.get("ip")
                if ip:
                    # Using region_province, city from the csv as ground truth if available
                    # The CSV has multiple columns like region_province, city, region(ip-API) etc.
                    # We will try to get the most reliable ones.
                    prov = row.get("region_province", "")
                    city = row.get("city", "")
                    # For region, we might just use province if region is not clearly defined, 
                    # but typically Tribun uses "Jawa", "Sumatra" etc. 
                    # For simplicity of this mock, we store what we have.
                    mapping[ip] = {
                        "city": city.strip(),
                        "province": prov.strip()
                    }
    except Exception as e:
        print(f"Failed to load IP mapping: {e}")
    
    IP_MAPPING_CACHE = mapping
    return mapping

def load_test_results(csv_path: str) -> List[TestRequest]:
    requests = []
    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row_num, row in enumerate(reader, start=2):
                endpoint = row.get("Endpoint", "")
                scenario = row.get("Scenario", "Legacy Data") # Fallback for old CSVs
                ip_address = row.get("IP Address", "")
                client_id = row.get("Client ID", "")
                mode = row.get("Mode", "")
                status_code = row.get("Status Code", "")
                latency = row.get("Latency (Seconds)", "N/A")
                model_code = row.get("Model Code", "")
                raw_res = row.get("Full Response / Error", "")
                
                req = TestRequest(
                    row_num=row_num,
                    endpoint=endpoint,
                    scenario=scenario,
                    ip_address=ip_address,
                    client_id=client_id,
                    mode=mode,
                    status_code=status_code,
                    latency_sec=float(latency) if latency != "N/A" else 0.0,
                    model_code=model_code,
                    raw_response=raw_res
                )
                
                # Parse JSON to extract articles
                if status_code == "200":
                    try:
                        data = json.loads(raw_res)
                        articles_data = []
                        if endpoint == "/article":
                            api_data = data.get("data", data)
                            if isinstance(api_data, list):
                                articles_data = api_data
                            elif isinstance(api_data, dict):
                                articles_data = api_data.get("recommended_article", data.get("recommended_article", []))
                            else:
                                articles_data = []
                        elif endpoint in ["/homepage", "/latest_feed"]:
                            api_data = data.get("data", [])
                            if isinstance(api_data, dict):
                                articles_data = api_data.get("recommended_article", [])
                            else:
                                articles_data = api_data
                            
                            try:
                                req.execution_time_ms = float(data.get("execution_time", 0))
                            except (ValueError, TypeError):
                                pass
                            
                        for item in articles_data:
                            req.articles.append(Article(
                                id=item.get("id"),
                                title=item.get("title", ""),
                                publish_date=item.get("publish_date", ""),
                                region=item.get("region", ""),
                                city=item.get("city", ""),
                                province=item.get("province", ""),
                                type=item.get("type", ""),
                                site=item.get("site", ""),
                                section_title=item.get("section_title", ""),
                                _feed_source=item.get("_feed_source"),
                                raw_json=item
                            ))
                    except json.JSONDecodeError:
                        pass
                
                requests.append(req)
    except Exception as e:
        print(f"Failed to load test results: {e}")
        
    return requests
