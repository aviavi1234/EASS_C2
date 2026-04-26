import json
from datetime import datetime
from io import StringIO

import httpx
import streamlit as st


DEFAULT_API_BASE = "http://127.0.0.1:8000"


def fetch_pois(api_base: str) -> list[dict]:
    response = httpx.get(f"{api_base}/pois/", timeout=10)
    response.raise_for_status()
    return response.json()


def create_poi(api_base: str, payload: dict) -> dict:
    response = httpx.post(f"{api_base}/pois/", json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def delete_poi(api_base: str, poi_id: int) -> None:
    response = httpx.delete(f"{api_base}/pois/{poi_id}", timeout=10)
    response.raise_for_status()


def update_poi(api_base: str, poi_id: int, payload: dict) -> dict:
    response = httpx.patch(f"{api_base}/pois/{poi_id}", json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def refresh_pois_cache(api_base: str) -> None:
    st.session_state["pois_cache"] = fetch_pois(api_base)


def build_csv(pois: list[dict]) -> str:
    if not pois:
        return "id,latitude,longitude,elevation,poi_type,status,description,created_at,updated_at\n"

    headers = [
        "id",
        "latitude",
        "longitude",
        "elevation",
        "poi_type",
        "status",
        "description",
        "created_at",
        "updated_at",
    ]
    buffer = StringIO()
    buffer.write(",".join(headers) + "\n")
    for poi in pois:
        row = []
        for header in headers:
            value = poi.get(header, "")
            text = str(value).replace('"', '""')
            row.append(f'"{text}"')
        buffer.write(",".join(row) + "\n")
    return buffer.getvalue()


st.set_page_config(page_title="C2 POI Dashboard", page_icon=":satellite:", layout="wide")
st.title("Command & Control - POI Dashboard")
st.caption("Fast interface for listing, creating, and exporting points of interest.")

with st.sidebar:
    st.header("Connection")
    api_base = st.text_input("Backend API URL", value=DEFAULT_API_BASE).rstrip("/")
    st.markdown("Start backend with: `python -m uvicorn backend.main:app --reload`")

col_form, col_list = st.columns([1, 2])

with col_form:
    st.subheader("Add New POI")
    with st.form("create_poi_form", clear_on_submit=True):
        latitude = st.number_input("Latitude", value=32.0853, format="%.6f")
        longitude = st.number_input("Longitude", value=34.7818, format="%.6f")
        elevation = st.number_input("Elevation", value=0.0, format="%.2f")
        poi_type = st.selectbox(
            "POI Type",
            ["unknown", "building", "soldier", "tank", "vehicle"],
        )
        status = st.selectbox(
            "Status",
            ["active", "destroyed", "investigating"],
        )
        description = st.text_input("Description (optional)")
        submitted = st.form_submit_button("Create POI")

    if submitted:
        payload = {
            "latitude": latitude,
            "longitude": longitude,
            "elevation": elevation,
            "poi_type": poi_type,
            "status": status,
            "description": description or None,
        }
        try:
            created = create_poi(api_base, payload)
            st.success(f"POI #{created['id']} created successfully.")
        except httpx.HTTPError as exc:
            st.error(f"Failed to create POI: {exc}")

with col_list:
    st.subheader("Current POIs")
    refresh = st.button("Refresh List")

    if refresh or "pois_cache" not in st.session_state:
        try:
            st.session_state["pois_cache"] = fetch_pois(api_base)
        except httpx.HTTPError as exc:
            st.session_state["pois_cache"] = []
            st.error(f"Failed to fetch POIs: {exc}")

    pois = st.session_state.get("pois_cache", [])

    # Small extra: quick operational metric.
    total = len(pois)
    active_count = sum(1 for poi in pois if poi.get("status") == "active")
    destroyed_count = sum(1 for poi in pois if poi.get("status") == "destroyed")
    investigating_count = sum(1 for poi in pois if poi.get("status") == "investigating")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total POIs", total)
    m2.metric("Active", active_count)
    m3.metric("Destroyed", destroyed_count)
    m4.metric("Investigating", investigating_count)

    selected_poi = None
    if pois:
        table_event = st.dataframe(
            pois,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
            hide_index=True,
            key="pois_table",
        )
        selected_rows = table_event.selection.get("rows", [])
        if selected_rows:
            selected_poi = pois[selected_rows[0]]
    else:
        st.info("No POIs yet. Create one from the form on the left.")

    st.subheader("Selected POI Actions")
    if selected_poi:
        st.caption(f"Selected POI: #{selected_poi['id']}")
        with st.form("selected_poi_actions_form"):
            edit_latitude = st.number_input(
                "Latitude",
                value=float(selected_poi.get("latitude", 0.0)),
                format="%.6f",
            )
            edit_longitude = st.number_input(
                "Longitude",
                value=float(selected_poi.get("longitude", 0.0)),
                format="%.6f",
            )
            edit_elevation = st.number_input(
                "Elevation",
                value=float(selected_poi.get("elevation", 0.0)),
                format="%.2f",
            )
            poi_type_options = ["unknown", "building", "soldier", "tank", "vehicle"]
            selected_type = selected_poi.get("poi_type", "unknown")
            edit_type = st.selectbox(
                "POI Type",
                poi_type_options,
                index=poi_type_options.index(selected_type)
                if selected_type in poi_type_options
                else 0,
            )
            status_options = ["active", "destroyed", "investigating"]
            selected_status = selected_poi.get("status", "active")
            edit_status = st.selectbox(
                "Status",
                status_options,
                index=status_options.index(selected_status)
                if selected_status in status_options
                else 0,
            )
            edit_description = st.text_input(
                "Description",
                value=selected_poi.get("description") or "",
            )
            action_col1, action_col2 = st.columns(2)
            save_clicked = action_col1.form_submit_button("Save Changes")
            delete_clicked = action_col2.form_submit_button(
                "Delete Selected POI", type="secondary"
            )

        if save_clicked:
            edit_payload = {
                "latitude": edit_latitude,
                "longitude": edit_longitude,
                "elevation": edit_elevation,
                "poi_type": edit_type,
                "status": edit_status,
                "description": edit_description or None,
            }
            try:
                updated = update_poi(api_base, int(selected_poi["id"]), edit_payload)
                st.success(f"POI #{updated['id']} updated successfully.")
                refresh_pois_cache(api_base)
                st.rerun()
            except httpx.HTTPError as exc:
                st.error(f"Failed to update POI: {exc}")

        if delete_clicked:
            try:
                delete_poi(api_base, int(selected_poi["id"]))
                st.success(f"POI #{selected_poi['id']} removed.")
                refresh_pois_cache(api_base)
                st.rerun()
            except httpx.HTTPError as exc:
                st.error(f"Failed to delete POI: {exc}")
    elif pois:
        st.caption("Select a row in the table above to edit or delete that POI.")

    # Small extra: export current list to JSON/CSV.
    export_col1, export_col2 = st.columns(2)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with export_col1:
        st.download_button(
            "Export JSON",
            data=json.dumps(pois, indent=2),
            file_name=f"pois_export_{timestamp}.json",
            mime="application/json",
            use_container_width=True,
        )
    with export_col2:
        st.download_button(
            "Export CSV",
            data=build_csv(pois),
            file_name=f"pois_export_{timestamp}.csv",
            mime="text/csv",
            use_container_width=True,
        )
