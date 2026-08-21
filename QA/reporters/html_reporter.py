import os
from typing import List, Dict, Any
from models import TestRequest, ValidationResult
import config
import html

class HTMLReporter:
    def __init__(self):
        self.total_tests = 0
        self.total_pass = 0
        self.total_fail = 0
        self.total_warning = 0
        self.total_error = 0
        self.cold_start_users = set()
        self.all_results = []
        self.latencies = []
        self.homepage_metrics = []

    def add_result(self, request: TestRequest, val_results: List[ValidationResult]):
        self.total_tests += 1
        
        if request.endpoint == "/homepage":
            try:
                lat_ms = float(request.latency_sec) * 1000 if request.latency_sec != "N/A" else 0
                exec_ms = request.execution_time_ms
                self.homepage_metrics.append({
                    "client_id": request.client_id,
                    "ip_address": request.ip_address,
                    "mode": request.mode,
                    "latency_ms": lat_ms,
                    "execution_time_ms": exec_ms,
                    "delta": lat_ms - exec_ms
                })
            except (ValueError, TypeError):
                pass


        if request.latency_sec != "N/A":
            try:
                self.latencies.append(float(request.latency_sec) * 1000)
            except ValueError:
                pass
                
        for vr in val_results:
            # Aggregate per validation result
            if vr.status == "FAIL": self.total_fail += 1
            elif vr.status == "WARNING": self.total_warning += 1
            elif vr.status == "ERROR": self.total_error += 1
            elif vr.status == "COLD START USER": 
                # This is technically a PASS, but we track the user uniquely
                self.total_pass += 1
                self.cold_start_users.add(request.client_id)
            else: self.total_pass += 1
            
            escaped_detail = html.escape(vr.detail)
            
            # If the status contains space, we might want to sanitize it for CSS class
            css_class = vr.status.replace(" ", "_")
            
            # Store details for table
            self.all_results.append({
                "row": request.row_num,
                "scenario": request.scenario,
                "client_id": request.client_id,
                "ip_address": request.ip_address,
                "endpoint": request.endpoint,
                "mode": request.mode,
                "area": vr.validator_name,
                "status": vr.status,
                "css_class": css_class,
                "detail": escaped_detail,
                "raw_data": getattr(vr, 'raw_data', {})
            })

    def generate_report(self, output_path: str = "validation_report.html"):
        avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0
        max_latency = max(self.latencies) if self.latencies else 0
        
        exec_times = [m["execution_time_ms"] for m in self.homepage_metrics if m["execution_time_ms"]]
        deltas = [m["delta"] for m in self.homepage_metrics if m["delta"]]
        
        avg_exec = sum(exec_times) / len(exec_times) if exec_times else 0
        max_exec = max(exec_times) if exec_times else 0
        
        avg_delta = sum(deltas) / len(deltas) if deltas else 0
        max_delta = max(deltas) if deltas else 0
        
        # Sort results: Group by client_id, then ip_address, then row
        self.all_results.sort(key=lambda x: (x["client_id"], x["ip_address"], x["row"]))

        # Count total validation rows
        total_rows = len(self.all_results)
        total_cold_starts = len(self.cold_start_users)

        observability_html = ""
        if self.homepage_metrics:
            observability_html = """
            <h2>Homepage Observability Summary</h2>
            <table>
                <tr>
                    <th>Client ID</th>
                    <th>IP Address</th>
                    <th>Mode</th>
                    <th>Latency (ms)</th>
                    <th>Execution Time (ms)</th>
                    <th>Delta (ms)</th>
                </tr>
            """
            
            # Sort homepage metrics: Client ID -> IP Address -> Mode
            self.homepage_metrics.sort(key=lambda x: (x["client_id"], x["ip_address"], x["mode"]))
            
            cur_client_id = None
            cur_ip = None
            for hm in self.homepage_metrics:
                if hm["client_id"] != cur_client_id:
                    cur_client_id = hm["client_id"]
                    observability_html += f'<tr style="background-color: #2c3e50; color: white;"><td colspan="6" style="padding: 12px;"><b>Client ID: {cur_client_id}</b></td></tr>'
                    cur_ip = None
                
                if hm["ip_address"] != cur_ip:
                    cur_ip = hm["ip_address"]
                    observability_html += f'<tr style="background-color: #dcdde1;"><td colspan="6"><b>📍 IP Address: {cur_ip}</b></td></tr>'
                    
                observability_html += f"""
                <tr>
                    <td>{hm["client_id"]}</td>
                    <td>{hm["ip_address"]}</td>
                    <td>{hm["mode"]}</td>
                    <td>{hm["latency_ms"]:.0f}</td>
                    <td>{hm["execution_time_ms"]:.0f}</td>
                    <td>{hm["delta"]:.0f}</td>
                </tr>
                """
            observability_html += "</table><br><hr>"

        html_parts = [f"""
        <html>
        <head>
            <title>TribunX Recommendation Validation Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                .summary {{ background: #f9f9f9; padding: 15px; border: 1px solid #ddd; margin-bottom: 20px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 14px; vertical-align: top; }}
                th {{ background-color: #f2f2f2; }}
                .PASS {{ color: green; font-weight: bold; }}
                .FAIL {{ color: red; font-weight: bold; }}
                .WARNING {{ color: orange; font-weight: bold; }}
                .ERROR {{ color: darkred; font-weight: bold; }}
                .COLD_START_USER {{ color: #1E3A8A; font-weight: bold; background-color: #DBEAFE; padding: 2px 4px; border-radius: 4px; }}
                .detail-cell {{ font-family: monospace; white-space: pre-wrap; }}
            </style>
        </head>
        <body>
            <h1>TribunX Recommendation Validation Report</h1>
            <div class="summary">
                <h2>Summary Metrics</h2>
                <p><strong>Config Used:</strong> MMR Lambda={config.MMR_LAMBDA}, Similarity Threshold={config.SIMILARITY_THRESHOLD}</p>
                <p><strong>Total Requests Analyzed:</strong> {self.total_tests}</p>
                <hr>
                <p><strong>Total Validation Rules Checked:</strong> {total_rows}</p>
                <ul>
                    <li class="PASS">PASS: {self.total_pass}</li>
                    <li class="FAIL">FAIL: {self.total_fail}</li>
                    <li class="WARNING">WARNING: {self.total_warning}</li>
                    <li class="ERROR">ERROR: {self.total_error}</li>
                    <li class="COLD_START_USER">COLD START USER: {total_cold_starts}</li>
                </ul>
                <hr>
                <p><strong>Avg Latency:</strong> {avg_latency:.0f} ms</p>
                <p><strong>Max Latency:</strong> {max_latency:.0f} ms</p>
                <p><strong>Avg Execution Time:</strong> {avg_exec:.0f} ms</p>
                <p><strong>Max Execution Time:</strong> {max_exec:.0f} ms</p>
                <p><strong>Avg Delta:</strong> {avg_delta:.0f} ms</p>
                <p><strong>Max Delta:</strong> {max_delta:.0f} ms</p>
            </div>
            
            {observability_html}
            
            <h2>Validation Details</h2>
            <table>
                <tr>
                    <th>Row</th>
                    <th>Scenario</th>
                    <th>Client ID</th>
                    <th>IP Address</th>
                    <th>Endpoint</th>
                    <th>Mode</th>
                    <th>Validation Area</th>
                    <th>Status</th>
                    <th>Detail</th>
                </tr>
        """]

        current_client_id = None
        current_ip = None
        client_colors = ["#ffffff", "#f8f9fa", "#f4f6f9", "#eef2f5", "#fdfbf7"]
        color_idx = -1

        for res in self.all_results:
            if res["client_id"] != current_client_id:
                current_client_id = res["client_id"]
                color_idx = (color_idx + 1) % len(client_colors)
                html_parts.append(f"""<tr style="background-color: #2c3e50; color: white;"><td colspan="9" style="padding: 12px;"><b>Client ID: {current_client_id}</b></td></tr>""")
                current_ip = None # Reset IP to trigger IP separator

            if res["ip_address"] != current_ip:
                current_ip = res["ip_address"]
                html_parts.append(f"""<tr style="background-color: #dcdde1;"><td colspan="9"><b>📍 IP Address: {current_ip}</b></td></tr>""")
            
            bg_color = client_colors[color_idx]
            
            # Custom Rendering for Similarity Validation
            if res["area"] == "Similarity Validation (RapidFuzz)" and "metrics" in res.get("raw_data", {}):
                rd = res["raw_data"]
                metrics = rd.get("metrics", {})
                warnings = rd.get("warnings", [])
                violations = rd.get("violations", [])
                
                # Format Top Metrics Box
                metrics_html = f"""
                <div style="background-color: #f8f9fa; padding: 10px; border-left: 4px solid #007bff; border-radius: 4px; margin-bottom: 10px; color: #333; font-size: 13px;">
                    <b>📊 MMR Observability Metrics</b><br>
                    Average Ratio: <b>{metrics.get('average_ratio', 0)}</b> | 
                    Max Ratio: <b>{metrics.get('max_ratio', 0)}</b> | 
                    Threshold: <b>{metrics.get('threshold_used', 0)}</b> |
                    Anomaly Gap: <b>{metrics.get('anomaly_gap_used', 0)}</b><br>
                    Total Evaluated: {metrics.get('total_pairs_checked', 0)} pairs | 
                    Warnings: <span style="color: {'orange' if warnings else 'green'};"><b>{metrics.get('warning_count', 0)}</b></span> |
                    Violations (Fails): <span style="color: {'red' if violations else 'green'};"><b>{metrics.get('violation_count', 0)}</b></span>
                </div>
                """
                
                # Format Warnings (Collapsible)
                warn_html = ""
                if warnings:
                    warn_html += f'<details style="margin-bottom: 8px;" open><summary style="cursor: pointer; font-weight: bold; color: #f0ad4e;">▶ Show Anomalies / Warnings ({len(warnings)} pairs)</summary>'
                    warn_html += '<ul style="margin-top: 5px; padding-left: 20px; font-size: 12px; background-color: #fcf8e3; padding: 10px; border-radius: 5px; border-left: 3px solid #f0ad4e;">'
                    for w in warnings:
                        warn_html += f"""
                        <li style="margin-bottom: 8px;">
                            <b style="color: #c9302c;">⚠️ {w.get('warning_message')}</b><br>
                            A: [{w.get('article_1_id')}] {html.escape(w.get('article_1_title_raw', ''))}<br>
                            B: [{w.get('article_2_id')}] {html.escape(w.get('article_2_title_raw', ''))}<br>
                            <table style="margin-top: 4px; width: auto; font-size: 11px; background-color: white;">
                                <tr><th>Ratio (Truth)</th><th>Token Sort</th><th>Token Set</th><th>Gap (Sort)</th><th>Gap (Set)</th></tr>
                                <tr>
                                    <td><b>{w.get('ratio_score')}</b></td>
                                    <td>{w.get('token_sort_score')}</td>
                                    <td>{w.get('token_set_score')}</td>
                                    <td style="color: {'red' if w.get('gap_sort') >= metrics.get('anomaly_gap_used', 25) else 'black'}"><b>{w.get('gap_sort')}</b></td>
                                    <td style="color: {'red' if w.get('gap_set') >= metrics.get('anomaly_gap_used', 25) else 'black'}"><b>{w.get('gap_set')}</b></td>
                                </tr>
                            </table>
                        </li>
                        """
                    warn_html += '</ul></details>'

                # Format Violations (Collapsible)
                viol_html = ""
                if violations:
                    viol_html += f'<details style="margin-bottom: 8px;"><summary style="cursor: pointer; font-weight: bold; color: #d9534f;">▶ Show Violations ({len(violations)} pairs)</summary>'
                    viol_html += '<ul style="margin-top: 5px; padding-left: 20px; font-size: 12px; background-color: #f2dede; padding: 10px; border-radius: 5px; border-left: 3px solid #d9534f;">'
                    for v in violations:
                        viol_html += f"""
                        <li style="margin-bottom: 6px;">
                            <b style="color: #d9534f;">Ratio: {v.get('ratio_score')}</b><br>
                            A: [{v.get('article_1_id')}] {html.escape(v.get('article_1_title_raw', ''))}<br>
                            B: [{v.get('article_2_id')}] {html.escape(v.get('article_2_title_raw', ''))}<br>
                        </li>
                        """
                    viol_html += '</ul></details>'
                
                detail_html = metrics_html + warn_html + viol_html

            else:
                # Default Rendering for other validators
                detail_html = f'<details><summary style="cursor: pointer; font-weight: bold; color: #007bff;">View / Hide Details</summary><pre style="white-space: pre-wrap; font-size: 12px; margin-top: 8px; max-height: 400px; overflow-y: auto; background: #282c34; color: #abb2bf; padding: 10px; border-radius: 5px;">{res["detail"]}</pre></details>'

            html_parts.append(f"""
                <tr style="background-color: {bg_color};">
                    <td>{res["row"]}</td>
                    <td>{res["scenario"]}</td>
                    <td>{res["client_id"]}</td>
                    <td>{res["ip_address"]}</td>
                    <td>{res["endpoint"]}</td>
                    <td>{res["mode"]}</td>
                    <td>{res["area"]}</td>
                    <td class="{res['css_class']}">{res["status"]}</td>
                    <td class="detail-cell">{detail_html}</td>
                </tr>
            """)

        html_parts.append("""
            </table>
        </body>
        </html>
        """)
        
        html_content = "".join(html_parts)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"\nReport generated successfully: {output_path}")
