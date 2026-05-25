import json
import uuid

def update_main():
    with open('frontend/c2_gui/main.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # The block to replace is inside tab_activity
    # From "with ui.tab_panel(tab_activity):" to "ui.button("Add new tier", ...)"
    # We will use string manipulation to replace it.

    old_code = '''            with ui.tab_panel(tab_activity):
                ui.label(
                    "Manage time-based activity tiers. The last row represents inactivity (no time limit)."
                ).classes("text-caption text-grey-5 q-mb-md")

                tiers_box = ui.column().classes("w-full gap-2")

                def load_tiers_ui() -> None:
                    tiers_box.clear()
                    try:
                        rows = _client().fetch_poi_activity_tiers()
                    except httpx.HTTPError as exc:
                        ui.notify(str(exc), type="negative")
                        return

                    tier_inputs = []

                    with tiers_box:
                        # Table Header
                        with ui.row().classes("w-full items-center gap-4 px-4 py-2 bg-black/20 rounded-md font-bold text-white"):
                            ui.label("Time less than (min)").classes("w-40")
                            ui.label("Color").classes("w-32")
                            ui.label("Actions").classes("flex-grow text-right")

                        for r in rows:
                            is_last = r["max_minutes"] is None
                            with ui.row().classes("w-full items-center gap-4 px-4 py-2 c2-settings-card"):
                                if is_last:
                                    ui.label("Inactivity (∞)").classes("w-40 text-grey-5 italic")
                                    min_inp = None
                                else:
                                    min_inp = ui.number(value=r["max_minutes"]).classes("w-40").props("outlined dense")

                                with ui.row().classes("w-32 items-center gap-2"):
                                    color_inp = ui.input(value=r["color"]).classes("w-24").props("outlined dense")
                                    # Small color preview circle
                                    ui.html(f'<div style="width:16px;height:16px;border-radius:50%;background-color:{r["color"]}"></div>')
                                    
                                tier_inputs.append({"id": r["id"], "min_inp": min_inp, "color_inp": color_inp, "is_last": is_last})

                                with ui.row().classes("flex-grow justify-end gap-2"):
                                    if not is_last:
                                        def del_tier(tier_id=r["id"]) -> None:
                                            try:
                                                _client().delete_poi_activity_tier(tier_id)
                                                ui.notify("Tier deleted", type="positive")
                                                load_tiers_ui()
                                            except httpx.HTTPError as exc:
                                                ui.notify(str(exc), type="negative")
                                                
                                        ui.button("Delete", on_click=del_tier).props("dense flat color=red rounded no-caps")

                        with ui.row().classes("w-full justify-end mt-2"):
                            def save_all() -> None:
                                try:
                                    for t_data in tier_inputs:
                                        payload = {"color": t_data["color_inp"].value}
                                        if not t_data["is_last"] and t_data["min_inp"] is not None:
                                            payload["max_minutes"] = int(t_data["min_inp"].value)
                                        _client().patch_poi_activity_tier(t_data["id"], payload)
                                    ui.notify("All tiers saved", type="positive")
                                    load_tiers_ui()
                                except httpx.HTTPError as exc:
                                    ui.notify(str(exc), type="negative")
                                    
                            ui.button("Save All Changes", on_click=save_all).props("color=primary rounded no-caps")

                load_tiers_ui()

                with ui.dialog() as new_tier_dialog, ui.card().classes("w-96 p-5 c2-settings-card"):
                    ui.label("Add Activity Tier").classes("text-subtitle1 text-white font-bold mb-2")
                    new_min = ui.number(label="New max min", value=30).classes("w-full mb-2").props("outlined")
                    new_color = ui.input(label="Color", value="#ffffff").classes("w-full mb-4").props("outlined")
                    
                    def add_tier() -> None:
                        try:
                            _client().create_poi_activity_tier({
                                "max_minutes": int(new_min.value),
                                "color": new_color.value
                            })
                            ui.notify("Tier added", type="positive")
                            new_tier_dialog.close()
                            load_tiers_ui()
                        except httpx.HTTPError as exc:
                            ui.notify(str(exc), type="negative")
                            
                    with ui.row().classes("w-full justify-end gap-2"):
                        ui.button("Cancel", on_click=new_tier_dialog.close).props("flat rounded color=white no-caps")
                        ui.button("Add Tier", on_click=add_tier).props("color=primary rounded no-caps")

                ui.button("Add new tier", icon="add", on_click=new_tier_dialog.open).props("color=secondary rounded no-caps mt-4")'''

    new_code = '''            with ui.tab_panel(tab_activity):
                ui.label(
                    "Manage time-based activity tiers. The last row represents inactivity (no time limit)."
                ).classes("text-caption text-grey-5 q-mb-md")

                tiers_box = ui.column().classes("w-full gap-2")

                def get_local_tiers():
                    default_tiers = [
                        {"id": 1, "max_minutes": 5, "color": "#00ff00"},
                        {"id": 2, "max_minutes": 15, "color": "#ffff00"},
                        {"id": 3, "max_minutes": 60, "color": "#ffa500"},
                        {"id": 4, "max_minutes": None, "color": "#ff0000"}
                    ]
                    return app.storage.user.get("activity_tiers", default_tiers)

                def load_tiers_ui() -> None:
                    tiers_box.clear()
                    rows = get_local_tiers()

                    # Sort them: numbers first, None last
                    rows.sort(key=lambda t: t["max_minutes"] if t["max_minutes"] is not None else float('inf'))

                    tier_inputs = []

                    with tiers_box:
                        # Table Header
                        with ui.row().classes("w-full items-center gap-4 px-4 py-2 bg-black/20 rounded-md font-bold text-white"):
                            ui.label("Time less than (min)").classes("w-40")
                            ui.label("Color").classes("w-32")
                            ui.label("Actions").classes("flex-grow text-right")

                        for r in rows:
                            is_last = r["max_minutes"] is None
                            with ui.row().classes("w-full items-center gap-4 px-4 py-2 c2-settings-card"):
                                if is_last:
                                    ui.label("Inactivity (∞)").classes("w-40 text-grey-5 italic")
                                    min_inp = None
                                else:
                                    min_inp = ui.number(value=r["max_minutes"]).classes("w-40").props("outlined dense")

                                with ui.row().classes("w-32 items-center gap-2"):
                                    color_inp = ui.input(value=r["color"]).classes("w-24").props("outlined dense")
                                    # Small color preview circle
                                    ui.html(f'<div style="width:16px;height:16px;border-radius:50%;background-color:{r["color"]}"></div>')
                                    
                                tier_inputs.append({"id": r.get("id"), "min_inp": min_inp, "color_inp": color_inp, "is_last": is_last})

                                with ui.row().classes("flex-grow justify-end gap-2"):
                                    if not is_last:
                                        def del_tier(tier_id=r.get("id")) -> None:
                                            t_list = get_local_tiers()
                                            t_list = [t for t in t_list if t.get("id") != tier_id]
                                            app.storage.user["activity_tiers"] = t_list
                                            ui.notify("Tier deleted", type="positive")
                                            load_tiers_ui()
                                                
                                        ui.button("Delete", on_click=del_tier).props("dense flat color=red rounded no-caps")

                        with ui.row().classes("w-full justify-end mt-2"):
                            def save_all() -> None:
                                new_tiers = []
                                for t_data in tier_inputs:
                                    tier = {"id": t_data["id"], "color": t_data["color_inp"].value}
                                    if not t_data["is_last"] and t_data["min_inp"] is not None:
                                        tier["max_minutes"] = int(t_data["min_inp"].value)
                                    else:
                                        tier["max_minutes"] = None
                                    new_tiers.append(tier)
                                app.storage.user["activity_tiers"] = new_tiers
                                ui.notify("All tiers saved", type="positive")
                                load_tiers_ui()
                                    
                            ui.button("Save All Changes", on_click=save_all).props("color=primary rounded no-caps")

                load_tiers_ui()

                with ui.dialog() as new_tier_dialog, ui.card().classes("w-96 p-5 c2-settings-card"):
                    ui.label("Add Activity Tier").classes("text-subtitle1 text-white font-bold mb-2")
                    new_min = ui.number(label="New max min", value=30).classes("w-full mb-2").props("outlined")
                    new_color = ui.input(label="Color", value="#ffffff").classes("w-full mb-4").props("outlined")
                    
                    def add_tier() -> None:
                        t_list = get_local_tiers()
                        import random
                        t_list.append({
                            "id": random.randint(10000, 99999),
                            "max_minutes": int(new_min.value),
                            "color": new_color.value
                        })
                        app.storage.user["activity_tiers"] = t_list
                        ui.notify("Tier added", type="positive")
                        new_tier_dialog.close()
                        load_tiers_ui()
                            
                    with ui.row().classes("w-full justify-end gap-2"):
                        ui.button("Cancel", on_click=new_tier_dialog.close).props("flat rounded color=white no-caps")
                        ui.button("Add Tier", on_click=add_tier).props("color=primary rounded no-caps")

                ui.button("Add new tier", icon="add", on_click=new_tier_dialog.open).props("color=secondary rounded no-caps mt-4")'''

    if old_code in content:
        content = content.replace(old_code, new_code)
        with open('frontend/c2_gui/main.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Success: Activity tiers logic replaced in frontend/c2_gui/main.py")
    else:
        print("Error: Could not find old_code in frontend/c2_gui/main.py")

if __name__ == "__main__":
    update_main()
