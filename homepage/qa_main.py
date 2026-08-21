import sys
import os
import glob
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir in sys.path:
    sys.path.remove(current_dir)
if '' in sys.path:
    sys.path.remove('')

root_dir = os.path.abspath(os.path.join(current_dir, '..'))
qa_dir = os.path.join(root_dir, 'QA')
sys.path.insert(0, qa_dir)
sys.path.insert(0, root_dir)

import config

from QA import data_loader
from QA.validators.latency_val import LatencyValidator
from homepage.validators.lf_count_val import LFCountValidator
from homepage.validators.lf_visual_dedup_val import LFVisualDedupValidator
from homepage.validators.lf_duplicate_id_val import LFDuplicateIdValidator
from homepage.validators.lf_geo_fallback_val import LFGeoFallbackValidator
from homepage.validators.lf_resilience_val import LFResilienceValidator
from homepage.validators.lf_sorting_val import LFSortingValidator
from QA.reporters.html_reporter import HTMLReporter

def get_latest_csv_file():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    output_dir = os.path.join(root_dir, "output", "csv_latestfeed")
    
    csv_files = glob.glob(os.path.join(output_dir, "latest_feed_*.csv"))
    if not csv_files:
        return None
    csv_files.sort(key=os.path.getmtime, reverse=True)
    return csv_files[0]

def main():
    print("Starting Latest Feed QA Validation Engine...")
    
    latest_csv = get_latest_csv_file()
    if not latest_csv:
        print("No CSV testing file found for latest feed. Please run test_latest_feed.py first.")
        sys.exit(1)
        
    print(f"Validating dataset: {latest_csv}")

    requests = data_loader.load_test_results(latest_csv)
    if not requests:
        print("No test data found in the CSV. Exiting.")
        sys.exit(1)
        
    # Only keep latest_feed endpoints
    requests = [req for req in requests if req.endpoint == "/latest_feed"]
    if not requests:
        print("No /latest_feed requests found in the CSV. Exiting.")
        sys.exit(1)
        
    print(f"Loaded {len(requests)} latest feed requests to validate.")

    validators = [
        LatencyValidator(),
        LFCountValidator(),
        LFVisualDedupValidator(),
        LFDuplicateIdValidator(),
        LFGeoFallbackValidator(),
        LFResilienceValidator(),
        LFSortingValidator()
    ]
    
    validation_context = {req.row_num: [] for req in requests}
    
    for req in requests:
        if req.status_code == "ERROR":
            continue
            
        for val in validators:
            results = val.validate(req)
            if results:
                validation_context[req.row_num].extend(results)
                
    unique_client_ids = []
    for req in requests:
        if req.status_code != "ERROR" and req.client_id not in unique_client_ids:
            unique_client_ids.append(req.client_id)
            
    batch_size = getattr(config, 'BATCH_SIZE', 10)
    
    basename = os.path.basename(latest_csv)
    timestamp_part = basename.replace("latest_feed_", "").replace(".csv", "")
        
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, ".."))
    report_dir = os.path.join(root_dir, "output", "html_latestfeed")
    os.makedirs(report_dir, exist_ok=True)
    
    current_time = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    
    if len(unique_client_ids) <= batch_size:
        reporter = HTMLReporter()
        for req in requests:
            if req.status_code == "ERROR":
                continue
            reporter.add_result(req, validation_context[req.row_num])
            
        report_path = os.path.join(report_dir, f"validation_report_latest_feed_{current_time}.html")
        reporter.generate_report(report_path)
        print(f"\nReport generated: {report_path}")
    else:

        batches = [unique_client_ids[i:i + batch_size] for i in range(0, len(unique_client_ids), batch_size)]
        generated_reports = []
        for i, batch_ids in enumerate(batches, 1):
            reporter = HTMLReporter()
            for req in requests:
                if req.status_code == "ERROR":
                    continue
                if req.client_id in batch_ids:
                    reporter.add_result(req, validation_context[req.row_num])
            
            batch_report_path = os.path.join(report_dir, f"report_latest_feed_{current_time}_batch_{i}.html")
            reporter.generate_report(batch_report_path)
            generated_reports.append(batch_report_path)
            
        print(f"\nGenerated {len(batches)} batch reports in {report_dir}:")
        for p in generated_reports:
            print(f" - {p}")
            
    print("\nLatest Feed Validation complete.")

if __name__ == "__main__":
    main()
