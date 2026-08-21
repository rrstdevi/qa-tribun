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
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QA Automation Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-color: #3b82f6;
            --accent-hover: #60a5fa;
            --glass-border: rgba(255, 255, 255, 0.08);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Inter', sans-serif; }

        body {
            background-color: var(--bg-color);
            color: var(--text-primary);
            min-height: 100vh;
            background-image:
                radial-gradient(at 0% 0%, hsla(253, 16%, 7%, 1) 0, transparent 50%),
                radial-gradient(at 50% 0%, hsla(225, 39%, 30%, 0.5) 0, transparent 50%),
                radial-gradient(at 100% 0%, hsla(339, 49%, 30%, 0.3) 0, transparent 50%);
            background-attachment: fixed;
            padding: 60px 20px;
        }

        .container { max-width: 1100px; margin: 0 auto; }

        header { text-align: center; margin-bottom: 60px; animation: fadeInDown 0.8s ease-out; }

        h1 {
            font-size: 3.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #60a5fa 0%, #a855f7 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 15px;
            letter-spacing: -1.5px;
        }

        p.subtitle {
            font-size: 1.2rem; color: var(--text-secondary); font-weight: 300;
            max-width: 600px; margin: 0 auto; line-height: 1.6;
        }

        .report-grid {
            display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 30px; animation: fadeInUp 0.8s ease-out forwards; opacity: 0; animation-delay: 0.2s;
        }

        .report-card {
            background: var(--card-bg); backdrop-filter: blur(16px);
            border: 1px solid var(--glass-border); border-radius: 20px; padding: 30px;
            transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
            position: relative; overflow: hidden; display: flex; flex-direction: column;
            justify-content: space-between; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }

        .report-card::before {
            content: ''; position: absolute; top: 0; left: -100%; width: 50%; height: 100%;
            background: linear-gradient(to right, transparent, rgba(255,255,255,0.03), transparent);
            transform: skewX(-20deg); transition: all 0.6s ease;
        }

        .report-card:hover { transform: translateY(-8px); box-shadow: 0 20px 40px rgba(0,0,0,0.4); border-color: rgba(255,255,255,0.15); }
        .report-card:hover::before { left: 150%; }

        .report-icon {
            font-size: 2.5rem; margin-bottom: 20px;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; display: inline-block;
        }

        .report-title { font-size: 1.4rem; font-weight: 600; margin-bottom: 12px; color: #ffffff; }

        .report-date { font-size: 0.95rem; color: var(--text-secondary); margin-bottom: 30px; display: flex; align-items: center; gap: 8px; }

        .view-btn {
            display: inline-flex; align-items: center; justify-content: center;
            background: rgba(59, 130, 246, 0.1); color: #60a5fa; text-decoration: none;
            padding: 12px 20px; border-radius: 12px; font-weight: 600; font-size: 0.95rem;
            transition: all 0.3s ease; border: 1px solid rgba(59, 130, 246, 0.2);
        }

        .view-btn:hover { background: var(--accent-color); color: white; box-shadow: 0 0 20px rgba(59,130,246,0.4); }

        .badge {
            position: absolute; top: 20px; right: 20px; background: rgba(148,163,184,0.1);
            color: var(--text-secondary); padding: 6px 12px; border-radius: 20px;
            font-size: 0.75rem; font-weight: 700; letter-spacing: 0.5px; border: 1px solid var(--glass-border);
        }

        .badge.latest {
            background: rgba(16,185,129,0.1); color: #10b981; border-color: rgba(16,185,129,0.2);
            box-shadow: 0 0 10px rgba(16,185,129,0.2); animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(16,185,129,0.4); }
            70% { box-shadow: 0 0 0 6px rgba(16,185,129,0); }
            100% { box-shadow: 0 0 0 0 rgba(16,185,129,0); }
        }
        @keyframes fadeInDown { from { opacity: 0; transform: translateY(-20px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>QA Automation Dashboard</h1>
            <p class="subtitle">Validation Reports for Tribun Data Product</p>
        </header>
        <div class="report-grid">
    </div>
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
footer = "\n        </div>\n    </div>\n</body>\n</html>"

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
