import sys
import os
import glob
from datetime import datetime

# Append parent directory to sys.path so we can import root 'config.py'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

import data_loader
from validators.latency_val import LatencyValidator
from validators.recency_val import RecencyValidator
from validators.rules_homepage import HomepageRulesValidator
from validators.rules_article import ArticleRulesValidator
from validators.localization_val import LocalizationValidator
from validators.cold_start_val import ColdStartValidator
from validators.similarity_val import SimilarityValidator
from validators.image_position_val import ImagePositionValidator
from validators.ip_duplicate_val import IPDuplicateTitleValidator
from validators.local_global_duplicate_val import LocalGlobalDuplicateValidator
from validators.section_title_val import SectionTitleValidator
from validators.sorting_val import SortingValidator
from reporters.html_reporter import HTMLReporter

def get_latest_csv_file():
    # Get absolute path to the 'Data Product' root directory
    # Current script is in: Data Product/qa_automation/main.py
    # Root is two levels up: Data Product/
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    output_dir = os.path.join(root_dir, config.OUTPUT_DIR)
    
    csv_files = glob.glob(os.path.join(output_dir, "testing_*.csv"))
    if not csv_files:
        # Fallback to old format if new format not found
        fallback = os.path.join(output_dir, "combined_api_latency_results.csv")
        if os.path.exists(fallback):
            return fallback
        return None
    # Sort by modification time, descending
    csv_files.sort(key=os.path.getmtime, reverse=True)
    return csv_files[0]

def main():
    print("Starting QA Automation Validation...")
    
    # 1. Find CSV
    latest_csv = get_latest_csv_file()
    if not latest_csv:
        print("No CSV testing file found in the output directory. Please run test.py first.")
        sys.exit(1)
        
    print(f"Validating dataset: {latest_csv}")

    # 2. Load Data
    print("Loading test results and IP mappings...")
    requests = data_loader.load_test_results(latest_csv)
    if not requests:
        print("No test data found in the CSV. Exiting.")
        sys.exit(1)
        
    # Filter based on configured endpoints
    validate_endpoints = getattr(config, "VALIDATE_ENDPOINTS", ["/homepage", "/article"])
    requests = [req for req in requests if req.endpoint in validate_endpoints]
    
    if not requests:
        print(f"No requests found for endpoints {validate_endpoints} in the CSV. Exiting.")
        sys.exit(1)
        
    print(f"Loaded {len(requests)} requests to validate.")

    # 3. Setup Validators
    validators = [
        LatencyValidator(),
        RecencyValidator(),
        HomepageRulesValidator(),
        ArticleRulesValidator(),
        LocalizationValidator(),
        SimilarityValidator(),
        ImagePositionValidator(),
        IPDuplicateTitleValidator(),
        SectionTitleValidator(),
        SortingValidator()
    ]
    
    cross_validators = [
        ColdStartValidator(),
        LocalGlobalDuplicateValidator()
    ]
    
    # 4. Execute Validation Engine
    # Tahap 1: Standard Validation
    validation_context = {req.row_num: [] for req in requests}
    
    for req in requests:
        if req.status_code == "ERROR":
            continue
            
        for val in validators:
            results = val.validate(req)
            if results:
                validation_context[req.row_num].extend(results)
                
    # Tahap 2: Cross Validation
    for cross_val in cross_validators:
        cross_val.validate_all(requests, validation_context)

    # Tahap 3: Reporting & Batching
    unique_client_ids = []
    for req in requests:
        if req.status_code != "ERROR" and req.client_id not in unique_client_ids:
            unique_client_ids.append(req.client_id)
            
    batch_size = getattr(config, 'BATCH_SIZE', 5)
    
    # Extract timestamp from CSV filename to use in HTML report
    basename = os.path.basename(latest_csv)
    timestamp_part = basename.replace("testing_", "").replace(".csv", "")
    if "combined" in timestamp_part:
        timestamp_part = "latest"
        
    # Output to 'qa_automation/output/' relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    report_dir = os.path.join(script_dir, "output")
    
    if len(unique_client_ids) <= batch_size:
        reporter = HTMLReporter()
        for req in requests:
            if req.status_code == "ERROR":
                continue
            reporter.add_result(req, validation_context[req.row_num])
            
        report_path = os.path.join(report_dir, f"validation_report_{timestamp_part}.html")
        reporter.generate_report(report_path)
    else:
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        batches = [unique_client_ids[i:i + batch_size] for i in range(0, len(unique_client_ids), batch_size)]
        
        generated_reports = []
        for i, batch_ids in enumerate(batches, 1):
            reporter = HTMLReporter()
            for req in requests:
                if req.status_code == "ERROR":
                    continue
                if req.client_id in batch_ids:
                    reporter.add_result(req, validation_context[req.row_num])
            
            batch_report_path = os.path.join(report_dir, f"report_{current_time}_batch_{i}.html")
            reporter.generate_report(batch_report_path)
            generated_reports.append(batch_report_path)
            
        print(f"\nGenerated {len(batches)} batch reports in {report_dir}:")
        for p in generated_reports:
            print(f" - {p}")
            
    print("\nValidation complete.")

if __name__ == "__main__":
    main()
