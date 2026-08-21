import os
import re
from datetime import datetime

import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
directory = os.path.join(script_dir, "output")
index_path = os.path.join(directory, "index.html")

# Pastikan file index_path ada, jika belum ada buat dari template dasar
if not os.path.exists(index_path):
    os.makedirs(directory, exist_ok=True)
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write('''<!DOCTYPE html>
<html>
<head><title>QA Reports</title></head>
<body>
    <h1>Automation Reports</h1>
    <div class="report-grid">
    </div>
</body>
</html>''')


# Read current index.html
with open(index_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the start and end of the report grid
start_marker = '<div class="report-grid">'

if start_marker not in content:
    print("Could not find start marker")
    exit(1)

parts = content.split(start_marker)
header = parts[0] + start_marker + "\n\n"
footer = "\n    </div>\n</body>\n</html>"

html_files = []

# Scan root output directory and reports_* subdirectories
for f in os.listdir(directory):
    path = os.path.join(directory, f)
    if os.path.isfile(path) and f.endswith('.html') and f != 'index.html':
        html_files.append(f)
    elif os.path.isdir(path) and (f.startswith("reports_") or f.startswith("html_")):
        for sub_f in os.listdir(path):
            if sub_f.endswith('.html'):
                html_files.append(f"{f}/{sub_f}")

reports = []
for file_path in html_files:
    file_name = os.path.basename(file_path)
    # Extract date and time
    # validation_report_20260617_154551.html
    # report_2026-06-17_15-14-01_batch_1.html
    
    # Trending Tag: report_20260821_113754.html
    
    match1 = re.search(r'validation_report_(\d{8})_(\d{6})\.html', file_name)
    match2 = re.search(r'report_(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})_batch_(\d+)\.html', file_name)
    match3 = re.search(r'report_(\d{8})_(\d{6})\.html', file_name)
    
    dt = None
    title = "Validation Report"
    
    if match1:
        date_str, time_str = match1.groups()
        dt = datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
    elif match2:
        date_str, time_str, batch_num = match2.groups()
        dt = datetime.strptime(f"{date_str}{time_str}", "%Y-%m-%d%H-%M-%S")
        title = f"Validation Report (Batch {batch_num})"
    elif match3:
        date_str, time_str = match3.groups()
        dt = datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
        title = "Trending Tag Validation"
    else:
        continue
        
    reports.append({
        'file': file_path,
        'dt': dt,
        'title': title
    })

reports.sort(key=lambda x: x['dt'], reverse=True)

# Generate HTML for all reports found
cards_html = []
for i, r in enumerate(reports):
    badge_class = "badge latest" if i == 0 else "badge"
    badge_text = "LATEST RUN" if i == 0 else "COMPLETED"
    
    date_formatted = r['dt'].strftime("%B %d, %Y &bull; %H:%M:%S")
    
    card = f'''            <!-- Report Card -->
            <div class="report-card">
                <div class="{badge_class}">{badge_text}</div>
                <div>
                    <div class="report-icon">📑</div>
                    <h2 class="report-title">{r['title']}</h2>
                    <div class="report-date">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                            stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="12" cy="12" r="10"></circle>
                            <polyline points="12 6 12 12 16 14"></polyline>
                        </svg>
                        {date_formatted}
                    </div>
                </div>
                <a href="{r['file']}" class="view-btn">View Detailed Report</a>
            </div>'''
    cards_html.append(card)

new_content = header + "\n\n".join(cards_html) + footer

with open(index_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"Updated index.html with all {len(reports)} reports found in the directory and sub-directories.")
