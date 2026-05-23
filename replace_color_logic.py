import sys

with open('frontend/c2_gui/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

import_old = "from datetime import datetime"
import_new = "from datetime import datetime, timezone"
content = content.replace(import_old, import_new)

color_logic_old = '''                opts = {
                    "title": (
                        f"#{poi['id']} {poi['poi_type']} "
                        f"({poi.get('created_by_username', '?')})"
                    ),
                }
                color = poi.get("color")
                label = str(poi.get("poi_type") or "unknowns").strip()'''

color_logic_new = '''                opts = {
                    "title": (
                        f"#{poi['id']} {poi['poi_type']} "
                        f"({poi.get('created_by_username', '?')})"
                    ),
                }
                
                # Compute color locally
                updated_at_str = poi.get("updated_at")
                color = "#888888"
                if updated_at_str:
                    try:
                        updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                        if updated_at.tzinfo is None:
                            updated_at = updated_at.replace(tzinfo=timezone.utc)
                        now = datetime.now(timezone.utc)
                        age_min = (now - updated_at).total_seconds() / 60.0
                        
                        default_tiers = [
                            {"id": 1, "max_minutes": 5, "color": "#00ff00"},
                            {"id": 2, "max_minutes": 15, "color": "#ffff00"},
                            {"id": 3, "max_minutes": 60, "color": "#ffa500"},
                            {"id": 4, "max_minutes": None, "color": "#ff0000"}
                        ]
                        tiers = app.storage.user.get("activity_tiers", default_tiers)
                        tiers.sort(key=lambda t: t["max_minutes"] if t["max_minutes"] is not None else float('inf'))
                        
                        for t in tiers:
                            if t["max_minutes"] is None:
                                color = t["color"]
                                break
                            if age_min < t["max_minutes"]:
                                color = t["color"]
                                break
                    except Exception:
                        pass
                
                label = str(poi.get("poi_type") or "unknowns").strip()'''

if color_logic_old in content:
    content = content.replace(color_logic_old, color_logic_new)
    with open('frontend/c2_gui/main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Success: color logic updated.")
else:
    print("Error: Could not find color logic")
