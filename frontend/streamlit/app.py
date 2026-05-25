import json
from datetime import datetime
from io import StringIO

import httpx
import streamlit as st

from frontend.shared.api_client import DEFAULT_API_BASE, C2Client

POI_TYPES = ["unknowns", "infentry", "tank"]


def get_client(api_base: str) -> C2Client:
    token = st.session_state.get("access_token")
    return C2Client(api_base=api_base, token=token)


def build_csv(pois: list[dict]) -> str:
    if not pois:
        return "id,latitude,longitude,elevation,poi_type,color,description,created_at,updated_at,created_by_username\n"

    headers = [
        "id",
        "latitude",
        "longitude",
        "elevation",
        "poi_type",
        "color",
        "description",
        "created_at",
        "updated_at",
        "created_by_username",
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
st.caption("Simple table view for listing, creating, filtering, and exporting points of interest.")

with st.sidebar:
    st.header("Connection")
    api_base = st.text_input("Backend API URL", value=DEFAULT_API_BASE).rstrip("/")
    st.markdown("Start backend with: `python -m uvicorn backend.main:app --reload`")

    st.header("API login")
    st.caption("The API requires a JWT. Use a seeded account (e.g. admin / admin1234).")
    if not st.session_state.get("access_token"):
        with st.form("api_login"):
            username = st.text_input("Username", value="admin")
            password = st.text_input("Password", value="admin1234", type="password")
            if st.form_submit_button("Connect"):
                try:
                    client = C2Client(api_base)
                    data = client.login(username, password)
                    st.session_state["access_token"] = data["access_token"]
                    st.session_state["api_user"] = data["username"]
                    st.rerun()
                except httpx.HTTPError as exc:
                    st.error(f"Login failed: {exc}")
    else:
        st.success(f"Connected as **{st.session_state.get('api_user', '?')}**")
        if st.button("Disconnect"):
            st.session_state.pop("access_token", None)
            st.session_state.pop("api_user", None)
            st.session_state.pop("pois_cache", None)
            st.rerun()

if not st.session_state.get("access_token"):
    st.info("Connect to the API from the sidebar to use this dashboard.")
    st.stop()

client = get_client(api_base)

col_form, col_list = st.columns([1, 2])

with col_form:
    st.subheader("Add New POI")
    with st.form("create_poi_form", clear_on_submit=True):
        latitude = st.number_input("Latitude", value=32.0853, format="%.6f")
        longitude = st.number_input("Longitude", value=34.7818, format="%.6f")
        elevation = st.number_input("Elevation", value=0.0, format="%.2f")
        poi_type = st.selectbox("POI Type", POI_TYPES)
        description = st.text_input("Description (optional)")
        submitted = st.form_submit_button("Create POI")

    if submitted:
        payload = {
            "latitude": latitude,
            "longitude": longitude,
            "elevation": elevation,
            "poi_type": poi_type,
            "description": description or None,
        }
        try:
            created = client.create_poi(payload)
            st.success(f"POI #{created['id']} created successfully.")
            st.session_state.pop("pois_cache", None)
        except httpx.HTTPError as exc:
            st.error(f"Failed to create POI: {exc}")

with col_list:
    st.subheader("Current POIs")
    refresh = st.button("Refresh List")

    if refresh or "pois_cache" not in st.session_state:
        try:
            st.session_state["pois_cache"] = client.fetch_pois()
        except httpx.HTTPError as exc:
            st.session_state["pois_cache"] = []
            st.error(f"Failed to fetch POIs: {exc}")

    pois = st.session_state.get("pois_cache", [])

    total = len(pois)

    st.metric("Total POIs", total)

    filter_type = st.selectbox("Filter by type", ["(all)"] + POI_TYPES)
    filter_text = st.text_input("Description contains")

    filtered = pois
    if filter_type != "(all)":
        filtered = [p for p in filtered if p.get("poi_type") == filter_type]
    if filter_text:
        needle = filter_text.lower()
        filtered = [
            p
            for p in filtered
            if p.get("description") and needle in p["description"].lower()
        ]

    selected_poi = None
    if filtered:
        table_event = st.dataframe(
            filtered,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
            hide_index=True,
            key="pois_table",
        )
        selected_rows = table_event.selection.get("rows", [])
        if selected_rows:
            selected_poi = filtered[selected_rows[0]]
    else:
        st.info("No POIs match the current filters.")

    st.subheader("Selected POI Actions")
    if selected_poi:
        st.caption(
            f"Selected POI: #{selected_poi['id']} "
            f"(by {selected_poi.get('created_by_username', '?')})"
        )
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
            selected_type = selected_poi.get("poi_type", "unknowns")
            edit_type = st.selectbox(
                "POI Type",
                POI_TYPES,
                index=POI_TYPES.index(selected_type)
                if selected_type in POI_TYPES
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
                "description": edit_description or None,
            }
            try:
                updated = client.update_poi(int(selected_poi["id"]), edit_payload)
                st.success(f"POI #{updated['id']} updated successfully.")
                st.session_state.pop("pois_cache", None)
                st.rerun()
            except httpx.HTTPError as exc:
                st.error(f"Failed to update POI: {exc}")

        if delete_clicked:
            try:
                client.delete_poi(int(selected_poi["id"]))
                st.success(f"POI #{selected_poi['id']} removed.")
                st.session_state.pop("pois_cache", None)
                st.rerun()
            except httpx.HTTPError as exc:
                st.error(f"Failed to delete POI: {exc}")
    elif pois:
        st.caption("Select a row in the table above to edit or delete that POI.")

    export_col1, export_col2 = st.columns(2)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with export_col1:
        st.download_button(
            "Export JSON",
            data=json.dumps(filtered, indent=2),
            file_name=f"pois_export_{timestamp}.json",
            mime="application/json",
            use_container_width=True,
        )
    with export_col2:
        st.download_button(
            "Export CSV",
            data=build_csv(filtered),
            file_name=f"pois_export_{timestamp}.csv",
            mime="text/csv",
            use_container_width=True,
        )
