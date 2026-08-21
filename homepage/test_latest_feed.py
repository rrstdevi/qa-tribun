"""
Latest Feed — Data Collector
============================
Mengumpulkan data respons dari endpoint /api/v3/homepage/recommendation?page_mode=latest
menggunakan matriks test case sesuai Latest_Feed_Test_Scenarios.md.

IP dibaca secara dinamis dari file IP address data.csv.
"""

import sys
import os
import csv
import json
import requests
from datetime import datetime

# Append parent directory agar config.py bisa diimport
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

# ============================================================
# KONFIGURASI TEST
# ============================================================

URL_LATEST_FEED = config.LATEST_FEED_BASE_URL + config.LATEST_FEED_ENDPOINT_PATH

HEADERS = {
    "accept": "application/json",
    "X-API-Key": config.API_KEY,
}

TEST_SCENARIOS = config.LATEST_FEED_TEST_SCENARIOS
LOCALIZED_MODES = config.LATEST_FEED_LOCALIZED_MODES

# Client IDs untuk test
def get_client_ids():
    cfg = config.CLIENT_ID_CONFIG
    ids = []
    if cfg.get("mode") == "range":
        start = cfg.get("range_start", 1)
        end = cfg.get("range_end", 5)
        for i in range(start, end + 1):
            ids.append(f"test-{i:03d}")
    elif cfg.get("mode") == "list":
        ids = cfg.get("list", [])
    return sorted(list(set(ids)))

def load_dynamic_ips():
    """Membaca IP dari config.IP_DATA_CSV_PATH dan extract unique IPs."""
    ip_matrix = []
    seen_ips = set()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, '..'))
    csv_path = os.path.join(root_dir, config.IP_DATA_CSV_PATH)
    
    if not os.path.exists(csv_path):
        print(f"Warning: File {csv_path} tidak ditemukan!")
        return ip_matrix

    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ip = row.get("ip")
            if ip and ip not in seen_ips:
                seen_ips.add(ip)
                # Mencoba mengambil info lokasi dari kolom yang ada
                city = row.get("city") or row.get("city(ip-API)") or ""
                prov = row.get("region_province") or row.get("region(ip-API)") or ""
                geo_note = f"{city}, {prov}".strip(", ")
                ip_matrix.append({
                    "ip": ip,
                    "label": f"IP from CSV | {city}",
                    "geo_note": geo_note
                })
    return ip_matrix

# ============================================================
# FUNGSI UTAMA
# ============================================================

def build_params(client_id: str, ip: str, localized: str, scenario: dict) -> dict:
    params = {
        "client_id": client_id,
        "ip_address": ip,
        "page_mode": config.LATEST_FEED_PAGE_MODE,
        "localized": localized,
    }
    if scenario.get("num_recommendation") is not None:
        params["num_recommendation"] = scenario["num_recommendation"]
    if scenario.get("source_url"):
        params["source_url"] = scenario["source_url"]
    return params

def hit_endpoint(params: dict, timeout: int = 15) -> tuple:
    try:
        resp = requests.get(URL_LATEST_FEED, params=params, headers=HEADERS, timeout=timeout)
        latency = resp.elapsed.total_seconds()
        status = resp.status_code

        if status == 200:
            data = resp.json()
            execution_time = data.get("execution_time", 0)
            articles = data.get("data", [])
            if isinstance(articles, dict):
                articles = articles.get("recommended_article", [])
            num_returned = len(articles) if isinstance(articles, list) else 0
            article_ids = [str(a.get("id", "")) for a in articles] if isinstance(articles, list) else []
            return status, latency, json.dumps(data), execution_time, num_returned, ", ".join(article_ids)
        else:
            return status, latency, resp.text, 0, 0, "N/A"

    except Exception as e:
        return "ERROR", "N/A", str(e), 0, 0, "N/A"

def run_data_collection():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, ".."))
    output_dir = os.path.join(root_dir, "output", "csv_latestfeed")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    csv_filename = os.path.join(output_dir, f"latest_feed_{timestamp}.csv")

    client_ids = get_client_ids()
    ip_matrix = load_dynamic_ips()
    
    if not client_ids:
        print("Tidak ada Client ID yang dikonfigurasi. Cek config.py → CLIENT_ID_CONFIG.")
        return
    if not ip_matrix:
        print("Tidak ada IP yang ditemukan di file CSV.")
        return

    total = len(TEST_SCENARIOS) * len(ip_matrix) * len(LOCALIZED_MODES) * len(client_ids)
    print(f"Starting Latest Feed Data Collection")
    print(f"  Scenarios : {len(TEST_SCENARIOS)}")
    print(f"  IP Matrix : {len(ip_matrix)} IPs (dinamis dari CSV)")
    print(f"  Modes     : {len(LOCALIZED_MODES)} (local/global/mix)")
    print(f"  Client IDs: {len(client_ids)}")
    print(f"  Total Hits: {total}\n")

    with open(csv_filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")

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
            "Full Response / Error",
            "TC IDs",
            "Geo Note",
            "Execution Time (ms)",
        ])

        for scenario in TEST_SCENARIOS:
            tc_id = scenario["tc_id"]
            scenario_label = f"{tc_id}: {scenario['name']}"
            print(f"\n{'='*60}")
            print(f"Scenario: {scenario_label}")
            print(f"{'='*60}")

            for ip_config in ip_matrix:
                ip = ip_config["ip"]
                geo_note = ip_config["geo_note"]

                for mode_cfg in LOCALIZED_MODES:
                    mode_val = mode_cfg["value"]
                    mode_label = mode_cfg["label"]

                    for client_id in client_ids:
                        params = build_params(client_id, ip, mode_val, scenario)
                        status, latency, raw_response, exec_time_ms, num_returned, id_string = hit_endpoint(params)

                        writer.writerow([
                            "/latest_feed",
                            scenario_label,
                            ip,
                            client_id,
                            mode_label,
                            status,
                            latency,
                            "N/A",
                            num_returned,
                            id_string,
                            raw_response,
                            tc_id,
                            geo_note,
                            exec_time_ms,
                        ])

                        status_display = f"[{status}]" if status in ("ERROR", "TIMEOUT", "CONN_ERROR") else f"HTTP {status}"
                        print(
                            f"  [{tc_id} | {mode_label:<9}] "
                            f"Client: {client_id} | "
                            f"IP: {ip:<16} | "
                            f"{status_display} | "
                            f"Articles: {num_returned} | "
                            f"Latency: {latency}s"
                        )

    print(f"\n{'='*60}")
    print(f"Data collection selesai!")
    print(f"Output: {csv_filename}")

if __name__ == "__main__":
    run_data_collection()
