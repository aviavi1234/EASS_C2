import sys

with open('frontend/api_client.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if "def fetch_poi_activity_tiers" in line:
        skip = True
    if "def _headers(self)" in line:
        skip = False
        
    if not skip:
        new_lines.append(line)

with open('frontend/api_client.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
