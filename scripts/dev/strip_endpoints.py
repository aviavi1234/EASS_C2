import sys

with open('backend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if line.startswith('@app.get("/poi-activity-tiers/"'):
        skip = True
    if line.startswith('@app.get("/users/"'):
        skip = False
    
    if not skip:
        new_lines.append(line)

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
