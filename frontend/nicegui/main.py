"""
Command & Control map UI (NiceGUI).

Run from repo root:
    python -m frontend.nicegui.main
    python -m frontend.nicegui.main --port 8081
"""

from __future__ import annotations

import argparse
import json
import math
import os
import socket
from datetime import datetime, timezone

import httpx
from nicegui import app, events, ui



from frontend.shared.api_client import DEFAULT_API_BASE, C2Client
from frontend.shared.settings import DEFAULT_ACTIVITY_TIERS, format_datetime, resolve_activity_color

FALLBACK_POI_TYPE_CODES = ["unknowns", "infentry", "tank"]

# Dark basemap aligned with NiceGUI / Quasar dark theme
DARK_TILE_URL = (
    "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
)
DARK_TILE_ATTRIBUTION = (
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> '
    '&copy; <a href="https://carto.com/attributions">CARTO</a>'
)

SATELLITE_TILE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
SATELLITE_TILE_ATTRIBUTION = "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"

MAP_PAGE_CSS = """
html, body, #app, .nicegui-content {
    margin: 0 !important;
    padding: 0 !important;
    height: 100% !important;
    max-height: 100% !important;
    overflow: hidden !important;
    background: #121212 !important;
}
.c2-fullmap {
    position: fixed !important;
    inset: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    z-index: 1;
    border-radius: 0 !important;
}
.c2-map-toolbar {
    position: fixed;
    top: 70px;
    right: 12px;
    z-index: 2000;
    gap: 4px;
}
.c2-map-hint {
    position: fixed !important;
    bottom: 130px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 2000;
    background: rgba(30, 30, 30, 0.92) !important;
    color: #e0e0e0 !important;
    padding: 8px 16px;
    border-radius: 20px;
    font-size: 13px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    pointer-events: none;
}
"""

SETTINGS_PAGE_CSS = """
.c2-settings-root {
    background: linear-gradient(180deg, #0d1117 0%, #121212 45%, #161d28 100%);
    min-height: 100vh;
}
.c2-settings-card {
    border-radius: 14px !important;
    background: rgba(28, 33, 44, 0.92) !important;
    border: 1px solid rgba(255, 255, 255, 0.07) !important;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4) !important;
}
.c2-settings-header {
    background: rgba(18, 22, 30, 0.92) !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    backdrop-filter: blur(10px);
}
.c2-settings-return-fab {
    position: fixed !important;
    bottom: 80px !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
    z-index: 8000 !important;
}
"""


import re
from pathlib import Path
from nicegui import app, events, ui

from backend.paths import POI_ICONS_DIR, USER_ICONS_DIR, ensure_data_dirs

# Serve icons locally so remote clients don't need the API host for marker images
ensure_data_dirs()
app.add_static_files("/local_icons", str(POI_ICONS_DIR))
app.add_static_files("/user_icons_static", str(USER_ICONS_DIR))

def _attach_password_validator(pwd_input, is_admin_check, submit_button_or_callback):
    with ui.column().classes("w-full text-xs mt-1 mb-2 gap-0"):
        req_len = ui.label("Length")
        req_num = ui.label("At least 1 number")
        req_spec = ui.label("At least 1 special character")
        req_case = ui.label("At least 1 uppercase & 1 lowercase")
        
    def check(*args):
        val = pwd_input.value or ""
        is_adm = is_admin_check() if callable(is_admin_check) else is_admin_check
        min_len = 12 if is_adm else 8
        req_len.text = f"At least {min_len} characters"
        
        has_len = len(val) >= min_len
        has_num = bool(re.search(r'\d', val))
        has_spec = bool(re.search(r'[^a-zA-Z0-9]', val))
        has_case = bool(re.search(r'[A-Z]', val)) and bool(re.search(r'[a-z]', val))
        
        req_len.classes(replace="text-positive" if has_len else "text-red")
        req_num.classes(replace="text-positive" if has_num else "text-red")
        req_spec.classes(replace="text-positive" if has_spec else "text-red")
        req_case.classes(replace="text-positive" if has_case else "text-red")
        
        valid = has_len and has_num and has_spec and has_case
        if not val:
            # If no password is typed (e.g. for update user where it's optional),
            # it might be valid if it's optional, but we will handle optional externally
            pass
            
        if callable(submit_button_or_callback):
            submit_button_or_callback(valid)
        elif valid:
            submit_button_or_callback.enable()
        else:
            submit_button_or_callback.disable()
            
        return valid

    pwd_input.on_value_change(check)
    # Don't call check() immediately here if button is not created yet!
    # Instead, we will defer it. But we want initial UI to show.
    # The callback will handle it gracefully.
    check()
    return check

def _primary_lan_ip() -> str | None:
    """Best-effort Wi‑Fi/LAN address for phone access instructions."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if not ip.startswith("127."):
                return ip
    except OSError:
        pass
    return None


def _client() -> C2Client:
    return C2Client(
        api_base=app.storage.user.get("api_base", DEFAULT_API_BASE),
        token=app.storage.user.get("token"),
    )


def _do_logout() -> None:
    try:
        _client().go_offline()
    except Exception:
        pass
    app.storage.user.pop("token", None)
    app.storage.user.pop("user", None)
    app.storage.user.pop("api_base", None)
    ui.navigate.to("/")


def _user() -> dict:
    return app.storage.user.get("user", {})


def _is_admin() -> bool:
    return _user().get("role") == "admin"


def _can_write() -> bool:
    user = _user()
    return user.get("role") == "admin" or user.get("permission") == "read_write"


def _display_permission(user: dict) -> str:
    if user.get("role") == "admin":
        return "read_write"
    return user.get("permission") or "read_only"


def _can_modify_poi(poi: dict) -> bool:
    if _is_admin():
        return True
    return poi.get("created_by_username") == _user().get("username")


def _require_login() -> None:
    if not app.storage.user.get("token"):
        ui.navigate.to("/")


def _format_dt(value: str | None) -> str:
    return format_datetime(
        value,
        date_format=app.storage.user.get("date_format", "dd.mm.yyyy"),
        time_format=app.storage.user.get("time_format", "24 hrs"),
    )


from frontend.shared.map_helpers import poi_hit_by_icon_click as _poi_hit_by_icon_click
from frontend.shared.map_helpers import unit_hit_by_icon_click as _unit_hit_by_icon_click


def _apply_map_tiles(map_el: ui.leaflet, is_satellite: bool) -> None:
    map_el.clear_layers()
    if is_satellite:
        # Base layer: Guaranteed global coverage up to zoom 13. Stretches if higher layers fail.
        map_el.tile_layer(
            url_template=SATELLITE_TILE_URL,
            options={
                "maxZoom": 19,
                "maxNativeZoom": 13,
                "attribution": SATELLITE_TILE_ATTRIBUTION,
            },
        )
        
        # Cascading high-resolution layers: from zoom 14 to 19.
        # This ensures we get the *best available* resolution before it falls back to the base layer.
        # ?blankTile=false forces a 404 error instead of gray "Map data not available" tiles.
        # errorTileUrl makes failed tiles transparent so lower-zoom layers show through.
        transparent_pixel = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        
        for z in range(14, 20):
            map_el.tile_layer(
                url_template=SATELLITE_TILE_URL + "?blankTile=false",
                options={
                    "minZoom": z,
                    "maxZoom": 19,
                    "maxNativeZoom": z,
                    "errorTileUrl": transparent_pixel,
                },
            )
    else:
        map_el.tile_layer(
            url_template=DARK_TILE_URL,
            options={
                "maxZoom": 19,
                "attribution": DARK_TILE_ATTRIBUTION,
            },
        )


@ui.page("/")
def login_page() -> None:
    ui.dark_mode().enable()
    ui.colors(primary="#5898d4", secondary="#26a69a", accent="#9c27b0")
    ui.add_css(SETTINGS_PAGE_CSS)
    ui.query("body").classes("c2-settings-root")

    with ui.column().classes("absolute-center w-full max-w-sm px-4"):
        with ui.card().classes("w-full p-8 c2-settings-card items-center gap-6"):
            with ui.column().classes("items-center gap-1"):
                ui.icon("public", size="3rem", color="primary")
                ui.label("Command & Control").classes("text-2xl font-bold text-white tracking-wide")
                ui.label("Sign in to open the operations map").classes("text-sm text-grey-5")

            saved_ip = app.storage.user.get("c2_server_ip", "127.0.0.1")
            saved_port = app.storage.user.get("c2_server_port", "8000")

            username = ui.input("Username").classes("w-full").props("outlined autocomplete=off")
            password = ui.input("Password", password=True).classes(
                "w-full"
            ).props("outlined autocomplete=new-password")
            
            with ui.expansion("Advanced Server Settings", icon="settings").classes("w-full bg-black/20 rounded-md mt-2"):
                server_ip = ui.input("Server IP", value=saved_ip).classes("w-full mb-2 mt-2").props("outlined")
                server_port = ui.input("Server Port", value=saved_port).classes("w-full mb-2").props("outlined")

                def _persist_server_settings() -> None:
                    ip = (server_ip.value or "").strip()
                    port = (server_port.value or "").strip()
                    if ip:
                        app.storage.user["c2_server_ip"] = ip
                    if port:
                        app.storage.user["c2_server_port"] = port

                server_ip.on_value_change(_persist_server_settings)
                server_port.on_value_change(_persist_server_settings)

            with ui.dialog() as setup_dialog, ui.card().classes("w-96 p-5 c2-settings-card"):
                ui.label("Initial Setup Required").classes("text-h6 text-white font-bold mb-2")
                ui.label("Please change your username and password to proceed.").classes("text-sm text-grey-4 mb-4")
                
                setup_username = ui.input("New Username").classes("w-full mb-2").props("outlined")
                setup_password = ui.input("New Password", password=True).classes("w-full mb-1").props("outlined")
                setup_password_confirm = ui.input("Repeat Password", password=True).classes("w-full mb-2 mt-2").props("outlined")
                
                setup_save_btn = None
                def toggle_setup_btn(valid):
                    if setup_save_btn:
                        if valid: setup_save_btn.enable()
                        else: setup_save_btn.disable()
                        
                check_fn = _attach_password_validator(
                    setup_password, 
                    lambda: app.storage.user.get("user", {}).get("role") == "admin", 
                    toggle_setup_btn
                )
                
                setup_save_btn = ui.button("Save and Continue").classes("w-full mt-4").props("color=primary rounded no-caps")
                check_fn()
                
                def do_setup():
                    if not setup_username.value or not setup_password.value:
                        ui.notify("Please fill all fields", type="negative")
                        return
                    if setup_password.value != setup_password_confirm.value:
                        ui.notify("Passwords do not match", type="negative")
                        return
                    
                    user_data = app.storage.user.get("user")
                    if not user_data:
                        return
                        
                    client = C2Client(app.storage.user.get("api_base"), app.storage.user.get("token"))
                    try:
                        client.patch_user(user_data["id"], {
                            "username": setup_username.value,
                            "password": setup_password.value,
                            "requires_setup": False
                        })
                        # Re-login with new credentials to get a fresh token
                        new_data = client.login(setup_username.value, setup_password.value)
                        app.storage.user["token"] = new_data["access_token"]
                        app.storage.user["user"] = new_data
                        setup_dialog.close()
                        ui.notify("Setup complete", type="positive")
                        ui.navigate.to("/map")
                    except httpx.HTTPError as exc:
                        ui.notify(f"Failed to update profile: {exc}", type="negative")

                setup_save_btn.on_click(do_setup)

            def do_login() -> None:
                ip = (server_ip.value or "127.0.0.1").strip()
                port = (server_port.value or "8000").strip()

                app.storage.user["c2_server_ip"] = ip
                app.storage.user["c2_server_port"] = port
                
                api_base_url = f"http://{ip}:{port}"
                try:
                    client = C2Client(api_base_url)
                    data = client.login(username.value, password.value)
                    app.storage.user["api_base"] = client.api_base
                    app.storage.user["token"] = data["access_token"]
                    app.storage.user["user"] = data
                    
                    if data.get("requires_setup"):
                        setup_dialog.open()
                    else:
                        ui.navigate.to("/map")
                except httpx.HTTPError as exc:
                    ui.notify(f"Login failed: {exc}", type="negative")

            ui.button("Log in", on_click=do_login).classes("w-full mt-2").props("rounded size=lg")
            ui.label("Default user: admin / admin1234").classes(
                "text-xs text-grey-6 text-center mt-2"
            )



def build_top_toolbar() -> None:
    user = _user()
    if not user:
        return
    with ui.header().classes('bg-[#1e1e1e]/90 text-white px-4 py-2 flex justify-between items-center z-50 text-sm border-b border-gray-800 backdrop-blur-sm'):
        with ui.row().classes('items-center gap-4'):
            ui.label(f"{user.get('username')}").classes("font-bold text-base text-primary")
        with ui.row().classes('items-center gap-4'):
            lat = float(user.get('unit_lat') or 0.0)
            lng = float(user.get('unit_lng') or 0.0)
            loc_lbl = ui.label(f"Loc: {lat:.6f}, {lng:.6f}").classes("font-mono text-grey-4 text-xs")
            
            def update_loc():
                u = _user()
                if u:
                    la = float(u.get('unit_lat') or 0.0)
                    lo = float(u.get('unit_lng') or 0.0)
                    loc_lbl.set_text(f"Loc: {la:.6f}, {lo:.6f}")
            ui.timer(2.0, update_loc)

def setup_exception_handler():
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        def handle_exception(loop, context):
            exc = context.get('exception')
            if isinstance(exc, ConnectionResetError) and getattr(exc, 'winerror', None) == 10054:
                return
            loop.default_exception_handler(context)
        loop.set_exception_handler(handle_exception)
    except RuntimeError:
        pass

app.on_startup(setup_exception_handler)

def build_footer() -> None:
    user = _user()
    if not user:
        return
        
    with ui.footer().classes('bg-[#1e1e1e] text-white px-4 py-2 flex justify-between items-center z-50 text-sm border-t border-gray-800'):
        with ui.row().classes('items-center gap-4'):
            ui.label(f"Role: {user.get('role')}").classes("font-mono text-grey-4")
            ui.label(f"Perm: {_display_permission(user)}").classes("font-mono text-grey-4")
            
        with ui.row().classes('items-center justify-end gap-4 flex-grow'):
            time_label = ui.label("").classes("font-mono font-bold")
            
            def update_time():
                from datetime import datetime, timezone
                date_fmt = app.storage.user.get("date_format", "dd.mm.yyyy")
                time_fmt = app.storage.user.get("time_format", "24 hrs")
                
                now = datetime.now()
                
                d_str = now.strftime("%d.%m.%Y") if date_fmt == "dd.mm.yyyy" else now.strftime("%m.%d.%Y")
                t_str = now.strftime("%H:%M:%S") if time_fmt == "24 hrs" else now.strftime("%I:%M:%S %p")
                    
                time_label.set_text(f"{d_str}   {t_str}")
                
            ui.timer(1.0, update_time)
            update_time()

def _leaflet_custom_unit_icon_expr(color: str | None, icon_url: str | None) -> str:
    color = color or "#5898d4"
    if not icon_url:
        html = f'<div style="width:28px;height:28px;border-radius:4px;background-color:{color};border:2px solid white;box-shadow:0 0 4px rgba(0,0,0,0.5);"></div>'
    else:
        html = f'<div style="width:36px;height:36px;border-radius:4px;background-color:{color};border:3px solid white;box-shadow:0 0 6px rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;"><img src="{icon_url}" style="width:20px;height:20px;object-fit:contain;" /></div>'

    opts = {
        "html": html,
        "className": "",
        "iconSize": [36, 36] if icon_url else [28, 28],
        "iconAnchor": [18, 18] if icon_url else [14, 14],
    }
    import json
    return "L.divIcon(" + json.dumps(opts) + ")"


def _leaflet_custom_icon_expr(color: str | None, icon_url: str | None) -> str:
    if color and not icon_url:
        html = f'<div style="width:24px;height:24px;border-radius:50%;background-color:{color};border:2px solid white;box-shadow:0 0 4px rgba(0,0,0,0.5);"></div>'
    elif color and icon_url:
        html = f'<div style="width:36px;height:36px;border-radius:50%;background-color:{color};border:3px solid white;box-shadow:0 0 6px rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;"><img src="{icon_url}" style="width:20px;height:20px;object-fit:contain;" /></div>'
    elif icon_url:
        opts = {
            "iconUrl": icon_url,
            "iconSize": [32, 32],
            "iconAnchor": [16, 32],
        }
        return "L.icon(" + json.dumps(opts) + ")"
    else:
        return "new L.Icon.Default()"

    opts = {
        "html": html,
        "className": "",
        "iconSize": [36, 36] if icon_url else [24, 24],
        "iconAnchor": [18, 18] if icon_url else [12, 12],
    }
    return "L.divIcon(" + json.dumps(opts) + ")"


@ui.page("/settings")
def settings_page() -> None:
    _require_login()
    ui.dark_mode().enable()
    ui.colors(primary="#5898d4", secondary="#26a69a", accent="#9c27b0")
    ui.add_css(SETTINGS_PAGE_CSS)
    build_footer()

    def go_to_map() -> None:
        ui.navigate.to("/map")

    ui.query("body").classes("c2-settings-root")

    build_top_toolbar()
    with ui.row().classes("w-full max-w-4xl mx-auto px-4 pt-6 pb-2 justify-between items-center"):
        ui.button("Back to map", icon="arrow_back", on_click=go_to_map).props("flat color=primary no-caps rounded")
        ui.label("Settings").classes("text-h6 text-white text-weight-medium")
        ui.button("Logout", icon="logout", on_click=_do_logout).props("flat color=red no-caps rounded")

    with ui.column().classes("w-full max-w-4xl mx-auto px-4 py-6 gap-5 pb-20"):
        with ui.tabs().classes("w-full bg-transparent").props("active-color=primary indicator-color=primary align=justify") as tabs:
            tab_general = ui.tab("General", icon="settings").classes("text-weight-bold")
            tab_my_unit = ui.tab("My Unit", icon="person_pin").classes("text-weight-bold")
            tab_activity = ui.tab("Activity", icon="schedule").classes("text-weight-bold")
            if _is_admin():
                tab_users = ui.tab("Users", icon="group").classes("text-weight-bold")
                tab_types = ui.tab("POI types", icon="category").classes("text-weight-bold")

        tab_by_key = {
            "general": tab_general,
            "my_unit": tab_my_unit,
            "activity": tab_activity,
        }
        if _is_admin():
            tab_by_key["users"] = tab_users
            tab_by_key["types"] = tab_types
        initial_tab = tab_by_key.get(app.storage.user.get("settings_tab"), tab_general)

        def _persist_settings_tab(e) -> None:
            for key, tab in tab_by_key.items():
                if e.args == tab:
                    app.storage.user["settings_tab"] = key
                    break

        with ui.tab_panels(tabs, value=initial_tab).classes("w-full q-mt-sm bg-transparent") as settings_panels:
            settings_panels.on("update:model-value", _persist_settings_tab)
            with ui.tab_panel(tab_general):
                ui.label("General Settings").classes("text-subtitle1 text-white font-bold mb-2")
                
                orig_date = app.storage.user.get("date_format", "dd.mm.yyyy")
                orig_time = app.storage.user.get("time_format", "24 hrs")
                
                date_sel = ui.select(["dd.mm.yyyy", "mm.dd.yyyy"], value=orig_date, label="Date Format").classes("w-full max-w-xs mb-4").props("outlined")
                time_sel = ui.select(["24 hrs", "12 hrs"], value=orig_time, label="Time Format").classes("w-full max-w-xs mb-4").props("outlined")
                
                gen_save_btn = ui.button("Save Changes").props("color=primary rounded no-caps")
                gen_save_btn.set_visibility(False)
                
                def check_gen_changes(*args):
                    gen_save_btn.set_visibility(date_sel.value != orig_date or time_sel.value != orig_time)
                
                date_sel.on_value_change(check_gen_changes)
                time_sel.on_value_change(check_gen_changes)
                
                def save_general(*args):
                    nonlocal orig_date, orig_time
                    app.storage.user["date_format"] = date_sel.value
                    app.storage.user["time_format"] = time_sel.value
                    orig_date = date_sel.value
                    orig_time = time_sel.value
                    check_gen_changes()
                    ui.notify("General settings saved", type="positive")
                    
                gen_save_btn.on_click(save_general)

            with ui.tab_panel(tab_my_unit):
                ui.label("Unit Settings").classes("text-subtitle1 text-white font-bold mb-4")
                
                u_data = _user()
                uid = u_data.get("id")
                
                with ui.column().classes("w-full max-w-sm gap-6"):
                
                    # Group 1: General Info
                    with ui.card().classes("w-full c2-settings-card p-4"):
                        ui.label("General Information").classes("text-subtitle2 text-grey-4 mb-2")
                        unit_name = ui.input("Unit Name", value=u_data.get("unit_name", "")).classes("w-full mb-2").props("outlined")
                        
                        try:
                            poi_types_list = [r["label"] for r in _client().fetch_poi_types()]
                        except Exception:
                            poi_types_list = ["Unknowns", "Infentry", "Tank"]
                        if not poi_types_list:
                            poi_types_list = ["Unknowns"]
                            
                        cur_type = u_data.get("unit_type")
                        if not cur_type:
                            cur_type = poi_types_list[0]
                        elif cur_type not in poi_types_list:
                            poi_types_list.append(cur_type)
                            
                        unit_type = ui.select(poi_types_list, value=cur_type, label="Unit Type").classes("w-full mb-2").props("outlined")
                        unit_desc = ui.input("Description", value=u_data.get("unit_description", "")).classes("w-full").props("outlined")

                    # Group 2: Location Tracking
                    with ui.card().classes("w-full c2-settings-card p-4"):
                        ui.label("Location Tracking").classes("text-subtitle2 text-grey-4 mb-2")
                        saved_loc_mode = app.storage.user.get("loc_mode", "Manual")
                        if saved_loc_mode == "GPS Sensor":
                            saved_loc_mode = "Auto"
                        loc_mode = ui.radio(["Manual", "Auto"], value=saved_loc_mode).props("inline").classes("mb-2")
                        
                        with ui.row().classes("w-full gap-2 items-center") as manual_row:
                            unit_lat = ui.number("Latitude", value=u_data.get("unit_lat") or 0.0, format="%.6f").classes("flex-grow").props("outlined dense")
                            unit_lng = ui.number("Longitude", value=u_data.get("unit_lng") or 0.0, format="%.6f").classes("flex-grow").props("outlined dense")

                    # Group 3: Display
                    with ui.card().classes("w-full c2-settings-card p-4"):
                        ui.label("Display").classes("text-subtitle2 text-grey-4 mb-2")
                        show_loc = ui.switch("Show my location on map", value=u_data.get("show_location", False)).classes("mb-4")
                        
                        with ui.row().classes("w-full items-center gap-4"):
                            ui.label("Unit Icon:").classes("text-white")
                            icon_url = u_data.get("unit_icon_url")
                            if icon_url:
                                icon_url = icon_url.replace("/users/icons/", "/user_icons_static/")
                            icon_img = ui.image(icon_url or "").classes("w-12 h-12").props("fit=contain")
                            no_icon_lbl = ui.label("—").classes("text-grey-5")
                            
                            if icon_url:
                                no_icon_lbl.set_visibility(False)
                            else:
                                icon_img.set_visibility(False)
                            
                            def on_unit_icon_upload(e):
                                try:
                                    data = e.content.read()
                                    name = e.name or "icon.png"
                                    resp = _client().upload_user_icon(uid, data, name)
                                    app.storage.user["user"] = resp
                                    ui.notify("Icon saved", type="positive")
                                    new_icon_url = resp.get("unit_icon_url")
                                    if new_icon_url:
                                        new_icon_url = new_icon_url.replace("/users/icons/", "/user_icons_static/")
                                        icon_img.set_source(new_icon_url)
                                        icon_img.set_visibility(True)
                                        no_icon_lbl.set_visibility(False)
                                        rm_icon_btn.set_visibility(True)
                                    settings_panels.set_value(tab_my_unit)
                                    app.storage.user["settings_tab"] = "my_unit"
                                    try:
                                        _client().ping()
                                    except Exception:
                                        pass
                                except Exception as exc:
                                    ui.notify(str(exc), type="negative")
                                    
                            def del_unit_icon():
                                try:
                                    resp = _client().delete_user_icon(uid)
                                    app.storage.user["user"] = resp
                                    ui.notify("Icon removed", type="positive")
                                    icon_img.set_visibility(False)
                                    no_icon_lbl.set_visibility(True)
                                    rm_icon_btn.set_visibility(False)
                                except Exception as exc:
                                    ui.notify(str(exc), type="negative")
                                    
                            up_unit = ui.upload(on_upload=on_unit_icon_upload, auto_upload=True).props("accept=image/* max-files=1").classes("hidden")
                            ui.button("Upload icon", on_click=lambda: up_unit.run_method("pickFiles")).props("color=secondary rounded no-caps")
                            rm_icon_btn = ui.button("Remove icon", on_click=del_unit_icon).props("color=red rounded no-caps flat")
                            if not icon_url:
                                rm_icon_btn.set_visibility(False)
                                
                    with ui.row().classes("w-full justify-end mt-2"):
                        unit_save_btn = ui.button("Save Unit Settings").props("color=primary rounded no-caps")
                        unit_save_btn.set_visibility(False)
                
                # Setup logic
                def on_loc_mode_change(e):
                    app.storage.user["loc_mode"] = e.value
                    if e.value == "Manual":
                        manual_row.set_visibility(True)
                    else:
                        manual_row.set_visibility(False)
                        request_location()
                loc_mode.on_value_change(on_loc_mode_change)
                manual_row.set_visibility(loc_mode.value == "Manual")

                def _unit_form_snapshot() -> dict:
                    return {
                        "unit_name": unit_name.value or "",
                        "unit_type": unit_type.value,
                        "unit_description": unit_desc.value or "",
                        "show_location": show_loc.value,
                        "unit_lat": round(float(unit_lat.value or 0), 6),
                        "unit_lng": round(float(unit_lng.value or 0), 6),
                    }

                saved_unit_snapshot = _unit_form_snapshot()
                suppress_unit_change_check = False

                def check_unit_changes(*args) -> None:
                    if suppress_unit_change_check:
                        return
                    dirty = _unit_form_snapshot() != saved_unit_snapshot
                    unit_save_btn.set_visibility(dirty)

                unit_name.on_value_change(check_unit_changes)
                unit_type.on_value_change(check_unit_changes)
                unit_desc.on_value_change(check_unit_changes)
                show_loc.on_value_change(check_unit_changes)
                unit_lat.on_value_change(check_unit_changes)
                unit_lng.on_value_change(check_unit_changes)

                # GPS JS
                async def request_location():
                    nonlocal suppress_unit_change_check, saved_unit_snapshot
                    if loc_mode.value != "Auto":
                        return
                    js_code = """
                        return new Promise((resolve, reject) => {
                            if (!window.isSecureContext && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
                                resolve({error: "GPS requires HTTPS connection. Please use localhost or HTTPS."});
                            } else if (!navigator.geolocation) {
                                resolve({error: "Geolocation not supported by this browser."});
                            } else {
                                navigator.geolocation.getCurrentPosition(
                                    (pos) => resolve({lat: pos.coords.latitude, lng: pos.coords.longitude}),
                                    (err) => resolve({error: err.message}),
                                    {enableHighAccuracy: true, timeout: 10000, maximumAge: 0}
                                );
                            }
                        });
                    """
                    try:
                        result = await ui.run_javascript(js_code, timeout=15.0)
                        if result and not result.get("error"):
                            new_lat = result.get("lat", 0.0)
                            new_lng = result.get("lng", 0.0)

                            resp = _client().patch_user(uid, {"unit_lat": new_lat, "unit_lng": new_lng})
                            app.storage.user["user"] = resp
                            try:
                                _client().ping()
                            except Exception:
                                pass

                            suppress_unit_change_check = True
                            try:
                                unit_lat.set_value(new_lat)
                                unit_lng.set_value(new_lng)
                            finally:
                                suppress_unit_change_check = False
                            saved_unit_snapshot = _unit_form_snapshot()
                            check_unit_changes()
                        elif result and result.get("error"):
                            ui.notify(f"GPS Error: {result['error']}", type="warning")
                    except Exception:
                        pass
                
                if loc_mode.value == "Auto":
                    ui.timer(15.0, request_location)
                else:
                    ui.timer(15.0, lambda: None)
                    
                def save_unit(*args):
                    nonlocal saved_unit_snapshot
                    payload = {
                        "unit_name": unit_name.value,
                        "unit_type": unit_type.value,
                        "unit_description": unit_desc.value,
                        "show_location": show_loc.value,
                        "unit_lat": float(unit_lat.value) if unit_lat.value else 0.0,
                        "unit_lng": float(unit_lng.value) if unit_lng.value else 0.0,
                    }
                    try:
                        resp = _client().patch_user(uid, payload)
                        app.storage.user["user"] = resp
                        saved_unit_snapshot = _unit_form_snapshot()
                        unit_save_btn.set_visibility(False)
                        try:
                            _client().ping()
                        except Exception:
                            pass
                        ui.notify("Unit settings saved", type="positive")
                    except Exception as exc:
                        ui.notify(str(exc), type="negative")
                        
                unit_save_btn.on_click(save_unit)

            with ui.tab_panel(tab_activity):
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
                            act_save_btn = ui.button("Save All Changes").props("color=primary rounded no-caps")
                            act_save_btn.set_visibility(False)
                            
                            def check_act_changes(*args):
                                act_save_btn.set_visibility(True)
                                
                            for t_data in tier_inputs:
                                if t_data["min_inp"]:
                                    t_data["min_inp"].on_value_change(check_act_changes)
                                t_data["color_inp"].on_value_change(check_act_changes)
                                
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
                                    
                            act_save_btn.on_click(save_all)

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

                ui.button("Add new tier", icon="add", on_click=new_tier_dialog.open).props("color=secondary rounded no-caps mt-4")
                

            if _is_admin():
                with ui.tab_panel(tab_users):
                    users_box = ui.column().classes("w-full gap-2")

                    def load_users_ui() -> None:
                        users_box.clear()
                        try:
                            users = _client().fetch_users()
                        except httpx.HTTPError as exc:
                            ui.notify(str(exc), type="negative")
                            return
                        with users_box:
                            with ui.row().classes("w-full items-center gap-4 px-4 py-2 bg-black/20 rounded-md font-bold text-white"):
                                ui.label("Username").classes("w-32")
                                ui.label("Role").classes("w-24")
                                ui.label("Permission").classes("w-32")
                                ui.label("Actions").classes("flex-grow text-right")

                            for u in users:
                                with ui.row().classes("w-full items-center gap-4 px-4 py-2 c2-settings-card"):
                                    ui.label(u['username']).classes("w-32 font-bold text-white")
                                    ui.label(u['role']).classes("w-24 text-grey-4")
                                    
                                    if u["role"] == "user":
                                        perm = ui.select(
                                            ["read_only", "read_write"],
                                            value=u.get("permission") or "read_only",
                                        ).props("outlined dense").classes("w-32")
                                    else:
                                        perm = None
                                        ui.label("—").classes("w-32 text-grey-6")
                                        
                                    with ui.row().classes("flex-grow justify-end gap-2 items-center"):
                                        if perm is not None:
                                            save_perm_btn = ui.button("Save").props("dense color=primary rounded no-caps")
                                            save_perm_btn.set_visibility(False)
                                            
                                            def on_perm_change(e, btn=save_perm_btn, orig=u.get("permission") or "read_only"):
                                                btn.set_visibility(e.value != orig)
                                                
                                            perm.on_value_change(on_perm_change)
                                            
                                            def save_perm(user=u, select=perm, btn=save_perm_btn) -> None:
                                                try:
                                                    _client().patch_user(user["id"], {"permission": select.value})
                                                    ui.notify("Permission updated", type="positive")
                                                    load_users_ui()
                                                except httpx.HTTPError as exc:
                                                    ui.notify(str(exc), type="negative")
                                                    
                                            save_perm_btn.on_click(save_perm)

                                        def open_edit_dialog(user=u) -> None:
                                            with ui.dialog() as edit_dialog, ui.card().classes("w-96 p-5 c2-settings-card"):
                                                ui.label("Edit Profile").classes("text-subtitle1 text-white font-bold mb-2")
                                                edit_name = ui.input("Username", value=user["username"]).props("outlined").classes("w-full mb-2")
                                                edit_pass = ui.input("New Password", password=True).props("outlined").classes("w-full mb-1")
                                                edit_pass_confirm = ui.input("Repeat Password", password=True).props("outlined").classes("w-full mb-2 mt-2")
                                                
                                                edit_btn = None
                                                def toggle_edit_btn(valid):
                                                    if edit_btn:
                                                        if valid: edit_btn.enable()
                                                        else: edit_btn.disable()
                                                        
                                                _attach_password_validator(edit_pass, user['role'] == 'admin', toggle_edit_btn)
                                                
                                                def save_changes():
                                                    payload = {}
                                                    if edit_name.value and edit_name.value != user["username"]:
                                                        payload["username"] = edit_name.value
                                                    if edit_pass.value:
                                                        if edit_pass.value != edit_pass_confirm.value:
                                                            ui.notify("Passwords do not match", type="negative")
                                                            return
                                                        payload["password"] = edit_pass.value
                                                    
                                                    if not payload:
                                                        ui.notify("No changes to save")
                                                        return
                                                        
                                                    try:
                                                        _client().patch_user(user["id"], payload)
                                                        ui.notify("User updated", type="positive")
                                                        edit_dialog.close()
                                                        if user["id"] == _user()["id"]:
                                                            _do_logout()
                                                        else:
                                                            load_users_ui()
                                                    except httpx.HTTPError as exc:
                                                        ui.notify(str(exc), type="negative")
                                                        
                                                with ui.row().classes("w-full justify-end gap-2"):
                                                    ui.button("Cancel", on_click=edit_dialog.close).props("flat rounded color=white no-caps")
                                                    edit_btn = ui.button("Save", on_click=save_changes).props("color=primary no-caps rounded")
                                                    
                                                # Trigger initial check now that button is created
                                                edit_pass.update()
                                            edit_dialog.open()

                                        ui.button("Change Username/Password", on_click=open_edit_dialog).props("dense color=secondary rounded no-caps")
                                        
                                        if u["username"] != _user()["username"]:
                                            def remove(user=u) -> None:
                                                try:
                                                    _client().delete_user(user["id"])
                                                    ui.notify("User deleted", type="positive")
                                                    load_users_ui()
                                                except httpx.HTTPError as exc:
                                                    ui.notify(str(exc), type="negative")

                                            ui.button("Delete", on_click=remove).props("dense flat color=red rounded no-caps")

                    load_users_ui()

                    with ui.dialog() as new_user_dialog, ui.card().classes("w-96 p-5 c2-settings-card"):
                        ui.label("Create user").classes("text-subtitle1 text-white font-bold mb-2")
                        new_name = ui.input("Username").props("outlined").classes("w-full mb-2")
                        new_pass = ui.input("Password", password=True).props("outlined").classes("w-full mb-1")
                        new_pass_confirm = ui.input("Repeat Password", password=True).props("outlined").classes("w-full mb-2 mt-2")
                        
                        create_state = {"role": "user"}
                        create_btn = None
                        def toggle_create_btn(valid):
                            if create_btn:
                                if valid: create_btn.enable()
                                else: create_btn.disable()
                                
                        check_fn = _attach_password_validator(new_pass, lambda: create_state["role"] == 'admin', toggle_create_btn)
                        
                        new_role = ui.select(
                            ["user", "admin"], value="user", label="Role"
                        ).props("outlined").classes("w-full mb-2 mt-2")
                        new_role.on_value_change(lambda e: [create_state.update({"role": e.value}), check_fn()])
                        
                        new_perm = ui.select(
                            ["read_only", "read_write"],
                            value="read_only",
                            label="Permission",
                        ).props("outlined").classes("w-full mb-4")

                        def create_user() -> None:
                            if new_pass.value != new_pass_confirm.value:
                                ui.notify("Passwords do not match", type="negative")
                                return
                                
                            payload = {
                                "username": new_name.value,
                                "password": new_pass.value,
                                "role": new_role.value,
                            }
                            if new_role.value == "user":
                                payload["permission"] = new_perm.value
                            try:
                                _client().create_user(payload)
                                ui.notify("User created", type="positive")
                                new_name.value = ""
                                new_pass.value = ""
                                new_pass_confirm.value = ""
                                new_user_dialog.close()
                                load_users_ui()
                            except httpx.HTTPError as exc:
                                ui.notify(str(exc), type="negative")

                        with ui.row().classes("w-full justify-end gap-2"):
                            ui.button("Cancel", on_click=new_user_dialog.close).props("flat rounded color=white no-caps")
                            create_btn = ui.button("Save", on_click=create_user).props("color=primary no-caps rounded")
                            
                        # Trigger initial check now that button is created
                        new_pass.update()

                    ui.button("Add new user", icon="add", on_click=new_user_dialog.open).props("color=secondary rounded no-caps mt-4")

                with ui.tab_panel(tab_types):
                    ui.label(
                        "Codes must be lowercase letters, digits, and underscores. "
                        "Upload a small PNG/JPEG/WebP for each type to show on the map."
                    ).classes("text-caption text-grey-5 q-mb-md")

                    types_box = ui.column().classes("w-full gap-3")

                    def load_types_ui() -> None:
                        types_box.clear()
                        try:
                            rows = _client().fetch_poi_types()
                        except httpx.HTTPError as exc:
                            ui.notify(str(exc), type="negative")
                            return
                        api_base = app.storage.user.get(
                            "api_base", DEFAULT_API_BASE
                        ).rstrip("/")
                        
                        type_inputs = []
                        
                        with types_box:
                            with ui.row().classes("w-full items-center gap-4 px-4 py-2 bg-black/20 rounded-md font-bold text-white"):
                                ui.label("Icon").classes("w-16")
                                ui.label("ID").classes("w-12")
                                ui.label("Label").classes("w-40")
                                ui.label("Actions").classes("flex-grow text-right")

                            for row in sorted(rows, key=lambda r: r["label"]):
                                with ui.row().classes("w-full items-center gap-4 px-4 py-2 c2-settings-card"):
                                    with ui.column().classes("w-16 items-center"):
                                        if row.get("icon_url"):
                                            filename = row["icon_url"].split("/")[-1]
                                            ui.image(f"/local_icons/{filename}").classes("w-8 h-8").props("fit=contain")
                                        else:
                                            ui.label("—").classes("text-grey-5")
                                            
                                    ui.label(f"#{row['id']}").classes("w-12 text-weight-bold")
                                    
                                    label_inp = ui.input(value=row["label"]).classes("w-40").props("outlined dense")
                                    
                                    type_inputs.append({"id": row["id"], "label_inp": label_inp})

                                    with ui.row().classes("flex-grow justify-end gap-2 items-center"):
                                        def del_row(r=row) -> None:
                                            try:
                                                _client().delete_poi_type(r["id"])
                                                ui.notify("Type removed", type="positive")
                                                load_types_ui()
                                            except httpx.HTTPError as exc:
                                                ui.notify(str(exc), type="negative")

                                        def on_icon_upload(e, tid=row["id"]) -> None:
                                            try:
                                                data = e.content.read()
                                                name = e.name or "icon.png"
                                                _client().upload_poi_type_icon(
                                                    tid, data, name
                                                )
                                                ui.notify("Icon saved", type="positive")
                                                load_types_ui()
                                            except httpx.HTTPError as exc:
                                                ui.notify(str(exc), type="negative")

                                        def del_icon(tid=row["id"]) -> None:
                                            try:
                                                _client().delete_poi_type_icon(tid)
                                                ui.notify("Icon removed", type="positive")
                                                load_types_ui()
                                            except Exception as exc:
                                                ui.notify(str(exc), type="negative")

                                        up = ui.upload(
                                            on_upload=on_icon_upload, auto_upload=True
                                        ).props("accept=image/* max-files=1").classes("hidden")
                                        ui.button("Upload icon", on_click=lambda u=up: u.run_method("pickFiles")).props("color=secondary rounded no-caps")
                                        if row.get("icon_url"):
                                            ui.button("Remove icon", on_click=del_icon).props("color=red rounded no-caps flat")
                                            
                                        ui.button("Delete", on_click=del_row).props(
                                            "dense flat color=red rounded no-caps"
                                        )

                            with ui.row().classes("w-full justify-end mt-2"):
                                types_save_btn = ui.button("Save All Changes").props("color=primary rounded no-caps")
                                types_save_btn.set_visibility(False)
                                
                                def check_types_changes(*args):
                                    types_save_btn.set_visibility(True)
                                    
                                for t_data in type_inputs:
                                    t_data["label_inp"].on_value_change(check_types_changes)
                                    
                                def save_all() -> None:
                                    try:
                                        for t_data in type_inputs:
                                            lbl = (t_data["label_inp"].value or "").strip()
                                            _client().update_poi_type(
                                                t_data["id"],
                                                {
                                                    "label": lbl,
                                                },
                                            )
                                        ui.notify("All types saved", type="positive")
                                        load_types_ui()
                                    except httpx.HTTPError as exc:
                                        ui.notify(str(exc), type="negative")
                                        
                                types_save_btn.on_click(save_all)

                    load_types_ui()

                    with ui.dialog() as new_type_dialog, ui.card().classes("w-96 p-5 c2-settings-card"):
                        ui.label("Add POI type").classes("text-subtitle1 text-white font-bold mb-2")
                        add_label = ui.input("Label", value="").props("outlined").classes("w-full mb-4")

                        def add_type() -> None:
                            label = (add_label.value or "").strip()
                            try:
                                _client().create_poi_type(
                                    {
                                        "label": label,
                                    }
                                )
                                ui.notify("Type created", type="positive")
                                add_label.value = ""
                                new_type_dialog.close()
                                load_types_ui()
                            except httpx.HTTPError as exc:
                                ui.notify(str(exc), type="negative")

                        with ui.row().classes("w-full justify-end gap-2"):
                            ui.button("Cancel", on_click=new_type_dialog.close).props("flat rounded color=white no-caps")
                            ui.button("Add type", on_click=add_type).props(
                                "color=primary no-caps rounded"
                            )

                    ui.button("Add new POI type", icon="add", on_click=new_type_dialog.open).props("color=secondary rounded no-caps mt-4")

    ui.button("Return to map", icon="map", on_click=go_to_map).classes(
        "c2-settings-return-fab"
    ).props("rounded color=primary push no-caps")

    def keep_unit_online() -> None:
        try:
            _client().ping()
        except Exception:
            pass

    ui.timer(10.0, keep_unit_online)


@ui.page("/map")
def map_page() -> None:
    _require_login()
    ui.dark_mode().enable()
    ui.colors(primary="#5898d4", secondary="#26a69a", accent="#9c27b0")
    ui.add_css(MAP_PAGE_CSS)
    build_top_toolbar()
    build_footer()

    pois_state: dict = {
        "items": [],
        "types": [],
        "type_by_label": {},
        "markers": {},
        "units": [],
        "unit_markers": {},
    }
    pending_marker_icons: list[tuple[object, str]] = []

    map_el = ui.leaflet(
        center=(32.0853, 34.7818), 
        zoom=11, 
        options={
            "zoomControl": False,
            "minZoom": 3,
            "worldCopyJump": True,
        }
    ).classes("c2-fullmap")
    _apply_map_tiles(map_el, app.storage.user.get("map_type", "dark") == "satellite")

    def _api_base() -> str:
        return app.storage.user.get("api_base", DEFAULT_API_BASE).rstrip("/")

    def refresh_poi_types_cache() -> list[str]:
        try:
            rows = _client().fetch_poi_types()
            pois_state["types"] = rows
            pois_state["type_by_label"] = {r["label"]: r for r in rows}
            labels = [r["label"] for r in sorted(rows, key=lambda x: x["label"])]
            return labels if labels else list(FALLBACK_POI_TYPE_CODES)
        except httpx.HTTPError:
            pois_state["types"] = []
            pois_state["type_by_label"] = {}
            return list(FALLBACK_POI_TYPE_CODES)

    def type_select_options(labels: list[str]) -> dict[str, str]:
        by = pois_state.get("type_by_label") or {}
        d: dict[str, str] = {}
        for l in labels:
            d[l] = l
        return d

    def flush_pending_marker_icons(_: events.GenericEventArguments) -> None:
        for layer, expr in pending_marker_icons:
            layer.run_method(":setIcon", expr)
        pending_marker_icons.clear()

    map_el.on("init", flush_pending_marker_icons)



    # --- Create POI dialog (map click) ---
    create_dialog = ui.dialog().props("persistent")
    with create_dialog, ui.card().classes("w-96 c2-settings-card"):
        ui.label("New point of interest").classes("text-lg font-bold text-white")
        create_lat = ui.number("Latitude", format="%.6f").classes("w-full mb-1").props("outlined")
        create_lng = ui.number("Longitude", format="%.6f").classes("w-full mb-1").props("outlined")
        create_elev = ui.number("Elevation", value=0.0).classes("w-full mb-1").props("outlined")
        _fb_opts = {c: c for c in FALLBACK_POI_TYPE_CODES}
        create_type = ui.select(_fb_opts, value="unknowns", label="Type").classes(
            "w-full mb-1"
        ).props("outlined")
        create_desc = ui.input("Description").classes("w-full mb-2").props("outlined")

        def submit_create() -> None:
            try:
                _client().create_poi(
                    {
                        "latitude": create_lat.value,
                        "longitude": create_lng.value,
                        "elevation": create_elev.value,
                        "poi_type": create_type.value,
                        "description": create_desc.value or None,
                    }
                )
                ui.notify("POI created", type="positive")
                create_dialog.close()
                update_pois_silently()
            except httpx.HTTPError as exc:
                ui.notify(str(exc), type="negative")

        with ui.row().classes("w-full justify-end gap-2 mt-2"):
            ui.button("Cancel", on_click=create_dialog.close).props("flat rounded color=white")
            ui.button("Create", on_click=submit_create).props("color=primary rounded no-caps")

    # --- POI detail / edit dialog (marker click) ---
    detail_dialog = ui.dialog()
    detail_form: dict = {}

    with detail_dialog, ui.card().classes("w-[26rem] max-w-[95vw] p-5 c2-settings-card"):
        detail_body = ui.column().classes("w-full gap-2")

    def open_create_dialog(lat: float, lng: float) -> None:
        codes = refresh_poi_types_cache()
        opts = type_select_options(codes)
        create_type.options = opts
        cur = "unknowns" if "unknowns" in opts else next(iter(opts))
        create_type.value = cur
        create_type.update()
        create_lat.value = lat
        create_lng.value = lng
        create_elev.value = 0.0
        create_desc.value = ""
        create_dialog.open()

    def _info_row(label: str, value: str) -> None:
        with ui.row().classes("w-full gap-2 items-start"):
            ui.label(label).classes("text-grey-5 w-28 shrink-0")
            ui.label(value).classes("flex-grow")

    def open_detail_dialog(poi: dict, *, focus_map: bool = True) -> None:
        if focus_map:
            map_el.set_center((poi["latitude"], poi["longitude"]))
        editable = _can_modify_poi(poi)
        detail_body.clear()
        detail_form.clear()
        with detail_body:
            if editable:
                ui.label("You can edit or delete this point.").classes(
                    "text-sm text-positive q-mb-sm"
                )
            else:
                ui.label("View only — you did not create this point.").classes(
                    "text-sm text-grey-5 q-mb-sm"
                )

            _info_row("Type", str(poi.get("poi_type", "—")))
            _info_row("Color", str(poi.get("color", "—")))
            _info_row("Created", _format_dt(poi.get("created_at")))
            _info_row("Updated", _format_dt(poi.get("updated_at")))
            _info_row("Created by", str(poi.get("created_by_username", "—")))
            _info_row(
                "Location",
                f"{poi.get('latitude', 0):.6f}, {poi.get('longitude', 0):.6f}",
            )
            _info_row("Elevation", str(poi.get("elevation", 0)))
            _info_row("Description", str(poi.get("description") or "—"))

            if editable:
                with ui.expansion('Edit POI', icon='edit').classes('w-full mt-4 bg-black/20 rounded-md'):
                    detail_form["lat"] = ui.number(
                        "Latitude", value=poi["latitude"], format="%.6f"
                    ).classes("w-full mb-1 mt-2").props("outlined")
                    detail_form["lng"] = ui.number(
                        "Longitude", value=poi["longitude"], format="%.6f"
                    ).classes("w-full mb-1").props("outlined")
                    detail_form["elev"] = ui.number(
                        "Elevation", value=poi.get("elevation") or 0.0
                    ).classes("w-full mb-1").props("outlined")
                    codes = refresh_poi_types_cache()
                    opts = type_select_options(codes)
                    cur_type = (poi.get("poi_type") or "unknowns") or "unknowns"
                    if cur_type not in opts:
                        opts = {**opts, cur_type: cur_type}
                    detail_form["ptype"] = ui.select(
                        opts, value=cur_type, label="Type"
                    ).classes("w-full mb-1").props("outlined")
                    detail_form["desc"] = ui.input(
                        "Description", value=poi.get("description") or ""
                    ).classes("w-full mb-2").props("outlined")

                    def save() -> None:
                        try:
                            _client().update_poi(
                                int(poi["id"]),
                                {
                                    "latitude": detail_form["lat"].value,
                                    "longitude": detail_form["lng"].value,
                                    "elevation": detail_form["elev"].value,
                                    "poi_type": detail_form["ptype"].value,
                                    "description": detail_form["desc"].value or None,
                                },
                            )
                            ui.notify("POI updated", type="positive")
                            detail_dialog.close()
                            update_pois_silently()
                        except httpx.HTTPError as exc:
                            ui.notify(str(exc), type="negative")

                    def delete() -> None:
                        try:
                            _client().delete_poi(int(poi["id"]))
                            ui.notify("POI deleted", type="positive")
                            detail_dialog.close()
                            update_pois_silently()
                        except httpx.HTTPError as exc:
                            ui.notify(str(exc), type="negative")

                    with ui.row().classes("w-full justify-end gap-2 mt-2"):
                        ui.button("Delete", on_click=delete, color="red").props("flat rounded color=red no-caps")
                        ui.button("Save changes", on_click=save).props("color=primary rounded no-caps")

            with ui.row().classes("w-full justify-end mt-2"):
                ui.button("Close", on_click=detail_dialog.close).props("flat rounded color=white no-caps")

        detail_dialog.open()

    def show_poi_picker() -> None:
        items = pois_state["items"]
        if not items:
            ui.notify("No points on the map yet", type="warning")
            return
        with ui.menu() as menu:
            for poi in sorted(items, key=lambda p: p["id"]):
                label = (
                    f"#{poi['id']} {poi['poi_type']} — "
                    f"{poi.get('created_by_username', '?')}"
                )

                def pick(p=poi) -> None:
                    menu.close()
                    open_detail_dialog(p)

                ui.menu_item(label, on_click=pick)
        menu.open()

    def update_pois_silently(*args, new_items: list | None = None) -> None:
        try:
            try:
                _client().ping()
            except Exception:
                pass
            if new_items is None:
                new_items = _client().fetch_pois()
            pois_state["items"] = new_items
            
            # Fetch units
            try:
                pois_state["units"] = _client().fetch_units()
            except Exception:
                pois_state["units"] = []
                
            base = _api_base()
            type_by = pois_state.get("type_by_label") or {}
            
            # Update Friendly Units
            new_unit_ids = set()
            for u in pois_state["units"]:
                uid = u["id"]
                
                opts = {
                    "title": (
                        f"Unit: {u.get('unit_name') or u['username']} "
                        f"({u.get('unit_type') or 'Unknown'})"
                    )
                }
                
                color = "#26a69a" # default friendly
                
                type_icon = None
                if u.get("unit_icon_url"):
                    filename = u["unit_icon_url"].split("/")[-1]
                    type_icon = f"/user_icons_static/{filename}"
                    
                expr = _leaflet_custom_unit_icon_expr(color, type_icon)
                
                lat = float(u.get("unit_lat") or 0.0)
                base_lng = float(u.get("unit_lng") or 0.0)
                
                for offset_lng, suffix in [(-360, "_left"), (0, ""), (360, "_right")]:
                    layer_id = f"{uid}{suffix}"
                    new_unit_ids.add(layer_id)
                    lng = base_lng + offset_lng
                    
                    if layer_id in pois_state["unit_markers"]:
                        layer = pois_state["unit_markers"][layer_id]
                        layer.run_method("setLatLng", [lat, lng])
                        if map_el.is_initialized:
                            layer.run_method(":setIcon", expr)
                    else:
                        layer = map_el.marker(latlng=(lat, lng), options=opts)
                        pois_state["unit_markers"][layer_id] = layer
                        if map_el.is_initialized:
                            layer.run_method(":setIcon", expr)
                        else:
                            pending_marker_icons.append((layer, expr))
                        
            to_delete_units = []
            for layer_id, layer in pois_state["unit_markers"].items():
                if layer_id not in new_unit_ids:
                    map_el.remove_layer(layer)
                    to_delete_units.append(layer_id)
            for layer_id in to_delete_units:
                del pois_state["unit_markers"][layer_id]
            
            new_ids = set()
            for poi in new_items:
                poi_id = poi["id"]
                
                opts = {
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
                        tiers = app.storage.user.get("activity_tiers", DEFAULT_ACTIVITY_TIERS)
                        color = resolve_activity_color(updated_at, tiers)
                    except Exception:
                        pass
                
                label = str(poi.get("poi_type") or "unknowns").strip()
                trow = type_by.get(label)
                type_icon = None
                if trow and trow.get("icon_url"):
                    filename = trow["icon_url"].split("/")[-1]
                    type_icon = f"/local_icons/{filename}"
                expr = _leaflet_custom_icon_expr(color, type_icon)

                lat = poi["latitude"]
                base_lng = poi["longitude"]
                
                for offset_lng, suffix in [(-360, "_left"), (0, ""), (360, "_right")]:
                    layer_id = f"{poi_id}{suffix}"
                    new_ids.add(layer_id)
                    lng = base_lng + offset_lng
                    
                    if layer_id in pois_state["markers"]:
                        layer = pois_state["markers"][layer_id]
                        layer.run_method("setLatLng", [lat, lng])
                        if map_el.is_initialized:
                            layer.run_method(":setIcon", expr)
                    else:
                        layer = map_el.marker(
                            latlng=(lat, lng),
                            options=opts,
                        )
                        pois_state["markers"][layer_id] = layer
                        if map_el.is_initialized:
                            layer.run_method(":setIcon", expr)
                        else:
                            pending_marker_icons.append((layer, expr))

            to_delete = []
            for layer_id, layer in pois_state["markers"].items():
                if layer_id not in new_ids:
                    map_el.remove_layer(layer)
                    to_delete.append(layer_id)
            for layer_id in to_delete:
                del pois_state["markers"][layer_id]
                
        except httpx.HTTPError:
            pass

    def plot_pois(center_map: bool = True) -> None:
        """Initial draw, optionally centers map."""
        pending_marker_icons.clear()
        map_el.clear_layers()
        _apply_map_tiles(map_el, app.storage.user.get("map_type", "dark") == "satellite")
        pois_state["markers"].clear()
        pois_state["unit_markers"].clear()
        
        items = pois_state["items"]
        if not items:
            return
            
        if center_map:
            avg_lat = sum(p["latitude"] for p in items) / len(items)
            avg_lng = sum(p["longitude"] for p in items) / len(items)
            map_el.set_center((avg_lat, avg_lng))
        
        # update markers and items
        update_pois_silently(new_items=items)

    unit_detail_dialog = ui.dialog()
    with unit_detail_dialog, ui.card().classes("w-[26rem] max-w-[95vw] p-6 c2-settings-card"):
        with ui.row().classes("w-full items-center justify-between mb-2"):
            ud_title = ui.label("Name").classes("text-primary text-2xl font-bold")
            ud_icon = ui.image().classes("w-12 h-12 rounded-md border border-white/20 shadow-md").props("fit=contain")
            
        with ui.column().classes("w-full gap-2"):
            ud_type = ui.label("Type:").classes("text-grey-4 text-sm font-mono")
            
            ui.separator().classes("bg-white/20 my-2")
            
            with ui.row().classes("w-full gap-3 items-start"):
                ui.icon("place", color="secondary", size="xs").classes("mt-1")
                ud_loc = ui.label("Location:").classes("text-white flex-grow font-mono")
                
            with ui.row().classes("w-full gap-3 items-start"):
                ui.icon("history", color="secondary", size="xs").classes("mt-1")
                ud_online = ui.label("Last online:").classes("text-white flex-grow")
                
            with ui.row().classes("w-full gap-3 items-start"):
                ui.icon("description", color="secondary", size="xs").classes("mt-1")
                ud_desc = ui.label("Description:").classes("text-white flex-grow italic")
            
        with ui.row().classes("w-full justify-end mt-6"):
            ui.button("Close", on_click=unit_detail_dialog.close).props("flat rounded color=primary no-caps")

    def open_unit_detail_dialog(unit: dict) -> None:
        icon_url = unit.get("unit_icon_url")
        if icon_url:
            filename = icon_url.split("/")[-1]
            ud_icon.set_source(f"/user_icons_static/{filename}")
            ud_icon.set_visibility(True)
        else:
            ud_icon.set_visibility(False)
            
        name = unit.get("unit_name") or unit.get("username")
        ud_title.set_text(name)
        ud_type.set_text(f"Unit Type: {unit.get('unit_type') or 'Unknown'}")
        
        lat = unit.get("unit_lat") or 0.0
        lng = unit.get("unit_lng") or 0.0
        ud_loc.set_text(f"{lat:.6f}, {lng:.6f}")
        
        online_str = unit.get('unit_last_online')
        if online_str:
            ud_online.set_text(_format_dt(online_str))
        else:
            ud_online.set_text("Unknown")
            
        ud_desc.set_text(unit.get('unit_description') or 'No description provided.')
        unit_detail_dialog.open()

    def on_map_click(e: events.GenericEventArguments) -> None:
        args = e.args or {}
        latlng = args.get("latlng") or {}
        lat = latlng.get("lat")
        lng = latlng.get("lng")
        if lat is None or lng is None:
            return
            
        lat = max(-90.0, min(90.0, float(lat)))
        # Wrap longitude endlessly so clicking far east/west works seamlessly
        lng = ((float(lng) + 180.0) % 360.0) - 180.0
        
        zoom = int(args.get("zoom") or 11)
        
        unit_hit = _unit_hit_by_icon_click(float(lat), float(lng), zoom, pois_state.get("units", []))
        if unit_hit:
            open_unit_detail_dialog(unit_hit)
            return
            
        hit = _poi_hit_by_icon_click(float(lat), float(lng), zoom, pois_state["items"])
        if hit:
            open_detail_dialog(hit)
            return
            
        if not _can_write():
            ui.notify("You have read-only access", type="warning")
            return
        open_create_dialog(float(lat), float(lng))

    map_el.on("map-click", on_map_click)

    def load_pois() -> None:
        try:
            refresh_poi_types_cache()
            pois_state["items"] = _client().fetch_pois()
            plot_pois()
        except httpx.HTTPError as exc:
            ui.notify(f"Failed to load POIs: {exc}", type="negative")

    with ui.row().classes("c2-map-toolbar"):
        def toggle_map_type():
            current = app.storage.user.get("map_type", "dark")
            new_type = "satellite" if current == "dark" else "dark"
            app.storage.user["map_type"] = new_type
            
            # Save the markers state before redrawing the tile layer
            # In nicegui, clear_layers removes all markers too, so we have to replot
            plot_pois(center_map=False)
            
        ui.button(icon="layers", on_click=toggle_map_type).props("flat round color=primary")
        ui.button(icon="refresh", on_click=update_pois_silently).props("flat round color=primary")
        ui.button(icon="settings", on_click=lambda: ui.navigate.to("/settings")).props(
            "flat round color=primary"
        )
        ui.button(
            icon="logout",
            on_click=_do_logout,
        ).props("flat round")

    load_pois()
    ui.timer(10.0, update_pois_silently)


def _pick_port(preferred: int, max_tries: int = 20) -> int:
    for offset in range(max_tries):
        port = preferred + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("0.0.0.0", port))
            except OSError:
                continue
            return port
    raise RuntimeError(
        f"No free port found in range {preferred}–{preferred + max_tries - 1}. "
        "Stop the other process or set C2_GUI_PORT / --port."
    )



def _ensure_self_signed_cert():
    from scripts.init.ssl import ensure_ssl_cert

    result = ensure_ssl_cert()
    return result is not None


def _start_http_redirect_server(*, https_port: int, http_port: int, lan_ip: str) -> None:
    """Plain HTTP port that redirects phones to HTTPS (mobile browsers often default to http:// for IPs)."""
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    https_url = f"https://{lan_ip}:{https_port}/"

    class RedirectHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = (
                "<!DOCTYPE html><html><head>"
                f'<meta http-equiv="refresh" content="0;url={https_url}">'
                "</head><body style='font-family:sans-serif;padding:1.5rem'>"
                f"<h2>C2 map — redirecting…</h2>"
                f'<p><a href="{https_url}">{https_url}</a></p>'
                "<p>Phones often open <b>http://</b> for IP addresses. "
                "That fails on the HTTPS port. This page sends you to HTTPS.</p>"
                "</body></html>"
            ).encode("utf-8")
            self.send_response(302)
            self.send_header("Location", https_url)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    def run() -> None:
        try:
            ThreadingHTTPServer(("0.0.0.0", http_port), RedirectHandler).serve_forever()
        except OSError as exc:
            print(f"[phone] HTTP redirect helper not started on port {http_port}: {exc}")

    threading.Thread(target=run, daemon=True).start()


def main() -> None:
    parser = argparse.ArgumentParser(description="C2 operations map (NiceGUI)")
    default_port = int(os.getenv("C2_GUI_PORT", "8081"))
    parser.add_argument("--port", type=int, default=default_port)
    parser.add_argument("--https", action="store_true", help="Enable HTTPS (required for mobile GPS)")
    args = parser.parse_args()
    port = _pick_port(args.port)
    if port != args.port:
        print(f"Port {args.port} is in use; starting on http://localhost:{port}")

    run_kwargs = {
        "title": "C2 Operations",
        "storage_secret": "c2-local-dev-secret-change-me",
        "reload": False,
        "port": port,
        "host": "0.0.0.0",
    }

    if args.https:
        from backend.paths import DEFAULT_CERT_FILE, DEFAULT_KEY_FILE

        if _ensure_self_signed_cert():
            run_kwargs["ssl_certfile"] = str(DEFAULT_CERT_FILE)
            run_kwargs["ssl_keyfile"] = str(DEFAULT_KEY_FILE)
            lan_ip = _primary_lan_ip()
            redirect_port = port + 1
            print("Starting with HTTPS enabled.")
            if lan_ip:
                print(f"  Phone (HTTPS): https://{lan_ip}:{port}")
                print(
                    f"  Phone (if browser picks HTTP): http://{lan_ip}:{redirect_port} "
                    "-> redirects to HTTPS"
                )
                _start_http_redirect_server(
                    https_port=port, http_port=redirect_port, lan_ip=lan_ip
                )
            print("  Type https:// manually - http:// on port", port, "shows 'page isn't working'.")
            print("  Accept the certificate warning (Advanced -> Proceed).")
            if lan_ip:
                print(
                    f"  Backend must listen on all interfaces: "
                    f"python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"
                )
                print(
                    f"  Login from phone: API Server IP = {lan_ip} "
                    "(Advanced Server Settings), not 127.0.0.1."
                )

    ui.run(**run_kwargs)


if __name__ in {"__main__", "__mp_main__"}:
    main()
