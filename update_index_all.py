import os
import re
from datetime import datetime

import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
directory = os.path.join(script_dir, "output")
index_path = os.path.join(directory, "index.html")

header = '''<!DOCTYPE html>
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
            background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 15px;
            letter-spacing: -1.5px;
        }

        p.subtitle {
            font-size: 1.2rem; color: var(--text-secondary); font-weight: 300;
            max-width: 600px; margin: 0 auto; line-height: 1.6;
        }

        .category-section { margin-bottom: 50px; }
        .category-title { 
            font-size: 2rem; font-weight: 600; margin-bottom: 25px; 
            color: #f8fafc; border-bottom: 2px solid var(--glass-border); 
            padding-bottom: 10px; animation: fadeInUp 0.8s ease-out forwards;
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
            -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; display: inline-block;
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
        </header>\n'''

footer = "\n    </div>\n</body>\n</html>"

html_files = []
target_dirs = ["html_trending_tag", "html_latestfeed", "html_cross_dedup"]

for target_dir in target_dirs:
    path = os.path.join(directory, target_dir)
    if os.path.isdir(path):
        for sub_f in os.listdir(path):
            if sub_f.endswith('.html'):
                html_files.append(f"{target_dir}/{sub_f}")

reports = []
for file_path in html_files:
    file_name = os.path.basename(file_path)
    match_trending = re.search(r'report_(\d{8})_(\d{6})\.html', file_name)
    match_latest = re.search(r'validation_report_latest_feed_(\d{2}-\d{2}-\d{4})_(\d{2}-\d{2}-\d{2})\.html', file_name)
    match_dedup = re.search(r'cross_dedup_(\d{2}-\d{2}-\d{4})_(\d{2}-\d{2}-\d{2})\.html', file_name)
    
    dt = None
    title = "Validation Report"
    
    if match_trending:
        date_str, time_str = match_trending.groups()
        dt = datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
        title = "Trending Tag Validation"
        category = "Trending Tag"
    elif match_latest:
        date_str, time_str = match_latest.groups()
        dt = datetime.strptime(f"{date_str}{time_str}", "%d-%m-%Y%H-%M-%S")
        title = "Latest Feed Validation"
        category = "Article based on location"
    elif match_dedup:
        date_str, time_str = match_dedup.groups()
        dt = datetime.strptime(f"{date_str}{time_str}", "%d-%m-%Y%H-%M-%S")
        title = "Cross Dedup Validation"
        category = "Cross deduplication"
    else:
        continue
        
    reports.append({
        'file': file_path,
        'dt': dt,
        'title': title,
        'category': category
    })

reports.sort(key=lambda x: x['dt'], reverse=True)

# Group reports
categories = ["Trending Tag", "Article based on location", "Cross deduplication"]
grouped_reports = {c: [] for c in categories}

for r in reports:
    if r['category'] in grouped_reports:
        grouped_reports[r['category']].append(r)

# Generate HTML for all reports found
sections_html = []
for category in categories:
    cat_reports = grouped_reports[category]
    if not cat_reports:
        continue
        
    section_html = f'''
        <div class="category-section">
            <h2 class="category-title">{category}</h2>
            <div class="report-grid">
'''
    cards_html = []
    for i, r in enumerate(cat_reports):
        badge_class = "badge latest" if i == 0 else "badge"
        badge_text = "LATEST RUN" if i == 0 else "COMPLETED"
        
        date_formatted = r['dt'].strftime("%B %d, %Y &bull; %H:%M:%S")
        
        card = f'''                <!-- Report Card -->
                <div class="report-card">
                    <div class="{badge_class}">{badge_text}</div>
                    <div>
                        <div class="report-icon">📑</div>
                        <h3 class="report-title">{r['title']}</h3>
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
        
    section_html += "\\n".join(cards_html)
    section_html += '''
            </div>
        </div>
'''
    sections_html.append(section_html)

new_content = header + "\\n".join(sections_html) + footer

with open(index_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"Updated index.html with all {len(reports)} reports found in the directory and sub-directories.")
