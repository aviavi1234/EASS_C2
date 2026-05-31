# Using the application

Screen-by-screen guide to the C2 frontends. Start the backend and UI first.

Screenshots are in `[docs/images/](images/)`.

---

## Overview


| UI                      | Exercise | URL (default)                                  | Purpose                                           |
| ----------------------- | -------- | ---------------------------------------------- | ------------------------------------------------- |
| **NiceGUI map**         | EX3      | [http://127.0.0.1:8081](http://127.0.0.1:8081) | Operations map — POIs, friendly units, GPS, admin |
| **Streamlit dashboard** | EX2      | [http://127.0.0.1:8501](http://127.0.0.1:8501) | Table view — list, filter, create, export POIs    |


Both talk to the same **FastAPI backend** on port **8000**. You sign in with a JWT; what you can do depends on your **role** and **permission** (see [Roles and permissions](#roles-and-permissions)).

---

## NiceGUI map (EX3)

### Login screen:


| Element                      | What it does                                                                                                       |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **Username / Password**      | Authenticates against the API. On a new database use `admin` / `admin1234`.                                        |
| **Advanced Server Settings** | Where the **GUI server** (on your PC) reaches the API. Default `**127.0.0.1:8000`** when the backend runs locally. |
| **Log in**                   | Opens the map, or the **Initial Setup** dialog if the account must change password on first login.                 |


> **First-time setup**
>
> After the default admin logs in once, a dialog asks for a **new username and password**. Password rules are shown live (length, number, special character, upper/lower case). Admin accounts have stricter rules. Click **Save and Continue** to reach the map.

### Operations map:

#### Screen layout


| Area                    | What it shows                                                                                                                                         |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Top bar (header)**    | Logged-in **username** and your unit **coordinates** (refreshed every 2 seconds).                                                                     |
| **Map**                 | Full-screen Leaflet map. **POIs** = round markers (color = activity age). **Friendly units** = square markers (users who enabled “Show my location”). |
| **Toolbar (top-right)** | See [Toolbar buttons](#toolbar-buttons).                                                                                                              |
| **Footer**              | **Role**, **permission**, and **date/time** (format from Settings → General).                                                                         |


#### Toolbar buttons


| Icon         | Action                                                   |
| ------------ | -------------------------------------------------------- |
| **Layers**   | Toggle **dark map** ↔ **satellite** imagery.             |
| **Refresh**  | Reload POIs and friendly units from the API immediately. |
| **Settings** | Open the [Settings page](#settings-page).                |
| **Logout**   | Clear session and return to login.                       |


The map also **auto-refreshes every 10 seconds**.

#### Map clicks


| You click…                          | What happens                                                            |
| ----------------------------------- | ----------------------------------------------------------------------- |
| **Empty map** (read/write or admin) | **New point of interest** dialog at that location (lat/lng pre-filled). |
| **Empty map** (read-only)           | Warning — cannot create POIs.                                           |
| **POI marker**                      | [POI detail](#poi-detail-and-edit) — view; edit/delete if allowed.      |
| **Friendly unit marker**            | Unit detail popup — name, type, location, last online, description.     |


POI **marker color** follows **activity tiers** (Settings → Activity): newer updates are greener; stale POIs shift toward the inactivity color.

### POI detail and edit:

**Creating a POI** — fill **Type**, **Elevation**, **Description** (optional); coordinates come from the map click. **Create** saves to the API; **Cancel** closes without saving.

**Viewing a POI** — the dialog shows type, color, created/updated times, creator, location, elevation, and description.

**Editing** — if you **own** the POI or are **admin**, expand **Edit POI** to change fields, then **Save changes**, or **Delete** to remove it. Other users’ POIs are view-only unless you are admin.

### Settings page:

Open from the map **gear** icon.

Settings — My Unit tab

#### General


| Setting         | Purpose                                     |
| --------------- | ------------------------------------------- |
| **Date format** | Footer clock: `dd.mm.yyyy` or `mm.dd.yyyy`. |
| **Time format** | Footer clock: 24-hour or 12-hour.           |


Click **Save Changes** after editing.

#### My Unit

Your operator profile on the map.


| Setting                            | Purpose                                                                                                                                    |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **Unit name / type / description** | Shown to others when they click your unit marker.                                                                                          |
| **Location tracking → Manual**     | Enter **latitude** and **longitude** yourself.                                                                                             |
| **Location tracking → Auto**       | Browser **GPS** updates your position every 15 seconds. On LAN/phone use `**--https`** when starting the map (see README troubleshooting). |
| **Show my location on map**        | When on, other users see your unit as a **friendly unit** marker (if you have a recent ping).                                              |
| **Unit icon**                      | Upload a custom image for your marker; **Remove icon** clears it.                                                                          |


Click **Save Unit Settings** when the button appears (after you change something).

#### Activity

Define **tiers** that control **POI marker colors** by time since last update:


| Column                   | Meaning                                                          |
| ------------------------ | ---------------------------------------------------------------- |
| **Time less than (min)** | Upper bound for this tier (e.g. 5 = “updated within 5 minutes”). |
| **Color**                | Hex color for POIs in that tier.                                 |
| **Inactivity (∞)**       | Last row — color for POIs older than all tiers.                  |


Use **Add new tier**, **Delete**, then **Save All Changes**. Stored in browser session (local UI setting).

#### Users *(admin only)*


| Action                         | Purpose                                       |
| ------------------------------ | --------------------------------------------- |
| **Permission dropdown + Save** | Set each user to `read_only` or `read_write`. |
| **Change Username/Password**   | Edit a user’s credentials.                    |
| **Delete**                     | Remove a user (cannot delete yourself).       |
| **Add new user**               | Create accounts with role and permission.     |


#### POI types *(admin only)*


| Action                             | Purpose                                                        |
| ---------------------------------- | -------------------------------------------------------------- |
| **Label field + Save All Changes** | Rename a POI type (updates existing POIs of that type).        |
| **Upload icon**                    | Custom marker icon for that type on the map.                   |
| **Remove icon / Delete**           | Clear icon or delete unused type (cannot delete types in use). |
| **Add new POI type**               | Create a new type label.                                       |


Use **Back to map** or **Return to map** at the bottom to leave Settings.

---

## Streamlit dashboard (EX2)

### Sidebar:


| Section                          | Purpose                                                                                                   |
| -------------------------------- | --------------------------------------------------------------------------------------------------------- |
| **Connection → Backend API URL** | API base URL (default `http://127.0.0.1:8000`).                                                           |
| **API login**                    | **Connect** with username/password; shows connected user when logged in. **Disconnect** clears the token. |


### Main area:


| Section                      | Purpose                                                                                 |
| ---------------------------- | --------------------------------------------------------------------------------------- |
| **Add New POI**              | Form: latitude, longitude, elevation, type, description → **Create POI**.               |
| **Current POIs**             | Table of all POIs; **Refresh List** reloads from API. **Total POIs** metric at top.     |
| **Filter by type**           | Show all or one POI type.                                                               |
| **Description contains**     | Text filter on description.                                                             |
| **Selected POI Actions**     | Click a **row** in the table, edit fields, **Save Changes** or **Delete Selected POI**. |
| **Export JSON / Export CSV** | Download the **currently filtered** list.                                               |


---

## Roles and permissions


| Role    | Permission   | POIs                                  | Admin tabs               |
| ------- | ------------ | ------------------------------------- | ------------------------ |
| `user`  | `read_only`  | View all; no create/edit/delete       | —                        |
| `user`  | `read_write` | Create; edit/delete **own** POIs only | —                        |
| `admin` | any          | Edit/delete **any** POI               | **Users**, **POI types** |


---

## Quick reference — GPS


| Where you use the map                 | Map command                               | Settings                                  |
| ------------------------------------- | ----------------------------------------- | ----------------------------------------- |
| **This PC** (`http://127.0.0.1:8081`) | Normal start (step 4 in README)           | **My Unit → Auto**                        |
| **Phone on same Wi‑Fi**               | Add `**--https`** (optional `**--port`**) | **Auto**; Server IP stays `**127.0.0.1`** |


