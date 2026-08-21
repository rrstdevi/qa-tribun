import sys
import os
import requests
import json
import csv
from datetime import datetime
from collections import namedtuple

# Append parent directory agar config.py bisa diimport
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

URL_RECOMMENDATION = config.LATEST_FEED_BASE_URL + config.LATEST_FEED_ENDPOINT_PATH
HEADERS = {
    "accept": "application/json",
    "X-API-Key": config.API_KEY,
}

def load_dynamic_ips():
    ip_matrix = []
    seen_ips = set()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, '..'))
    csv_path = os.path.join(root_dir, config.IP_DATA_CSV_PATH)
    
    if not os.path.exists(csv_path):
        return ip_matrix

    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ip = row.get("ip")
            if ip and ip not in seen_ips:
                seen_ips.add(ip)
                city = row.get("city") or row.get("city(ip-API)") or "Unknown"
                ip_matrix.append((ip, city))
    return ip_matrix

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

def fetch_feed(client_id, ip, mode, page_mode):
    params = {
        "client_id": client_id,
        "ip_address": ip,
        "page_mode": page_mode,
        "localized": mode,
        "num_recommendation": 20
    }
    
    try:
        resp = requests.get(URL_RECOMMENDATION, params=params, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            api_data = data.get("data", [])
            if isinstance(api_data, dict):
                articles = api_data.get("recommended_article", [])
            else:
                articles = api_data
                
            extracted = []
            for a in articles:
                site = str(a.get("site", "")).strip().lower()
                art_id = str(a.get("id", "")).strip()
                # Unique ID: gabungkan site dan ID
                unique_id = f"{site}_{art_id}" if site else art_id
                
                extracted.append({
                    "id": unique_id,
                    "title": str(a.get("title", "")).strip().lower(),
                    "foto": str(a.get("foto", "")).strip()
                })
            return extracted
    except Exception as e:
        print(f"Error fetching {page_mode}: {e}")
    return []

def check_internal_dups(articles):
    """Cek duplikasi di dalam feed yang sama (berdasarkan ID)."""
    seen_ids = set()
    dup_ids = set()
    for a in articles:
        uid = a["id"]
        if uid in seen_ids:
            dup_ids.add(uid)
        seen_ids.add(uid)
    return list(dup_ids)

def run_dedup_test():
    client_ids = get_client_ids()
    client_id = client_ids[0] if client_ids else "test-001"
    
    ip_matrix = load_dynamic_ips()
    modes = config.LATEST_FEED_LOCALIZED_MODES
    
    print("=" * 70)
    print("CROSS-FEED DEDUPLICATION TEST (Homepage vs Latest Feed)")
    print("=" * 70)
    print(f"Client ID : {client_id}")
    print(f"Total IPs : {len(ip_matrix)}")
    
    total_tests = 0
    failed_tests = 0
    report_data = []

    for ip, city in ip_matrix:
        for mode_dict in modes:
            mode = mode_dict["value"]
            mode_label = mode_dict["label"]
            
            print(f"\nTesting IP: {ip:<15} ({city}) | Mode: {mode_label}")
            
            # Hit APIs
            home_articles = fetch_feed(client_id, ip, mode, "homepage")
            latest_articles = fetch_feed(client_id, ip, mode, "latest")
            
            if not home_articles or not latest_articles:
                print("  -> SKIPPED (One or both endpoints returned empty/failed)")
                continue
                
            total_tests += 1
            
            # 1. Cek INTERNAL duplicates
            home_internal_dups = check_internal_dups(home_articles)
            latest_internal_dups = check_internal_dups(latest_articles)
            
            # 2. Cek CROSS duplicates
            home_ids = set(a["id"] for a in home_articles if a["id"])
            home_titles = set(a["title"] for a in home_articles if a["title"])
            home_fotos = set(a["foto"] for a in home_articles if a["foto"])
            
            cross_dup_ids = []
            cross_dup_titles = []
            cross_dup_fotos = []
            
            for la in latest_articles:
                if la["id"] in home_ids:
                    cross_dup_ids.append(la["id"])
                if la["title"] in home_titles:
                    cross_dup_titles.append(la["title"])
                if la["foto"] in home_fotos:
                    cross_dup_fotos.append(la["foto"])
                    
            has_internal = bool(home_internal_dups) or bool(latest_internal_dups)
            has_cross = bool(cross_dup_ids) or bool(cross_dup_titles) or bool(cross_dup_fotos)
            
            issue_endpoints = []
            if home_internal_dups:
                issue_endpoints.append("homepage (internal)")
            if latest_internal_dups:
                issue_endpoints.append("latest_feed (internal)")
            if has_cross:
                issue_endpoints.append("homepage & latest_feed (cross)")
            
            endpoint_str = ", ".join(issue_endpoints) if issue_endpoints else "-"
            
            status = "FAIL" if has_internal or has_cross else "PASS"
            
            # Record for reports
            report_data.append({
                "Client ID": client_id,
                "IP": ip,
                "City": city,
                "Mode": mode_label,
                "Status": status,
                "Issue Endpoint": endpoint_str,
                "Internal Dups": ", ".join(home_internal_dups + latest_internal_dups) if has_internal else "None",
                "Cross Dup IDs": ", ".join(set(cross_dup_ids)) if cross_dup_ids else "None",
                "Cross Dup Titles": " | ".join(set(cross_dup_titles)) if cross_dup_titles else "None",
                "Cross Dup Fotos": " | ".join(set(cross_dup_fotos)) if cross_dup_fotos else "None"
            })
            
            if status == "PASS":
                print("  -> [PASS] No duplication found.")
            else:
                failed_tests += 1
                print("  -> [FAIL] Duplication detected!")
                
                # Report Internal Duplicates
                if has_internal:
                    print("     [INTERNAL DUPLICATES - Same Endpoint]")
                    if home_internal_dups:
                        print(f"       - Homepage feed contains duplicate IDs: {', '.join(home_internal_dups)}")
                    if latest_internal_dups:
                        print(f"       - Latest feed contains duplicate IDs  : {', '.join(latest_internal_dups)}")
                
                # Report Cross Duplicates
                if has_cross:
                    print("     [CROSS DUPLICATES - Homepage vs Latest Feed]")
                    if cross_dup_ids:
                        print(f"       - Duplicate IDs   : {', '.join(set(cross_dup_ids))}")
                    if cross_dup_titles:
                        print(f"       - Duplicate Titles: {' | '.join(set(cross_dup_titles))}")
                    if cross_dup_fotos:
                        print(f"       - Duplicate Fotos : {' | '.join(set(cross_dup_fotos))}")

    print("=" * 70)
    print(f"TEST COMPLETED. Run: {total_tests}, Failed: {failed_tests}, Passed: {total_tests - failed_tests}")
    print("=" * 70)
    
    # Generate CSV and HTML Reports
    if report_data:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.abspath(os.path.join(script_dir, '..'))
        timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        
        # Paths
        csv_dir = os.path.join(root_dir, "output", "csv_cross_dedup")
        html_dir = os.path.join(root_dir, "output", "html_cross_dedup")
        os.makedirs(csv_dir, exist_ok=True)
        os.makedirs(html_dir, exist_ok=True)
        
        csv_path = os.path.join(csv_dir, f"cross_dedup_{timestamp}.csv")
        html_path = os.path.join(html_dir, f"cross_dedup_{timestamp}.html")
        
        # Write CSV
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=report_data[0].keys())
            writer.writeheader()
            writer.writerows(report_data)
            
        # Write HTML
        html_content = f"""
        <html>
        <head>
            <title>Cross-Feed Deduplication Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .pass {{ color: green; font-weight: bold; }}
                .fail {{ color: red; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h2>Cross-Feed Deduplication Report</h2>
            <p><strong>Generated:</strong> {timestamp}</p>
            <table>
                <tr>
        """
        for k in report_data[0].keys():
            html_content += f"<th>{k}</th>"
        html_content += "</tr>"
        
        for row in report_data:
            status_class = "pass" if row["Status"] == "PASS" else "fail"
            html_content += "<tr>"
            for k, val in row.items():
                if k == "Status":
                    html_content += f"<td class='{status_class}'>{val}</td>"
                else:
                    html_content += f"<td>{val}</td>"
            html_content += "</tr>"
            
        html_content += """
            </table>
        </body>
        </html>
        """
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        print("\nReports successfully generated:")
        print(f" -> CSV : {csv_path}")
        print(f" -> HTML: {html_path}")

if __name__ == "__main__":
    run_dedup_test()
