import sys

with open('backend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add DELETE /users/{user_id}/icon
delete_user_icon = '''@app.delete("/users/{user_id}/icon", response_model=UserPublic)
def delete_user_unit_icon(
    user_id: int,
    session: Session = Depends(db.get_session),
    current_user: User = Depends(get_current_user),
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this user")

    if user.unit_icon_filename and safe_icon_basename(user.unit_icon_filename):
        old = user_icons_directory() / user.unit_icon_filename
        if old.is_file():
            old.unlink()
            
    user.unit_icon_filename = None
    session.add(user)
    session.commit()
    session.refresh(user)
    return _user_to_public(user)'''

if "def delete_user_unit_icon(" not in content:
    content = content.replace("@app.get(\"/users/icons/{filename}\")", delete_user_icon + "\n\n@app.get(\"/users/icons/{filename}\")")

# 2. Add DELETE /poi-types/{type_id}/icon
delete_poi_icon = '''@app.delete("/poi-types/{type_id}/icon", response_model=PoiTypePublic)
def delete_poi_type_icon(
    type_id: int,
    session: Session = Depends(db.get_session),
    _: User = Depends(require_admin),
):
    poi_type = session.get(PoiTypeDefinition, type_id)
    if not poi_type:
        raise HTTPException(status_code=404, detail="POI type not found")

    if poi_type.icon_filename and safe_icon_basename(poi_type.icon_filename):
        old = icons_directory() / poi_type.icon_filename
        if old.is_file():
            old.unlink()

    poi_type.icon_filename = None
    session.add(poi_type)
    session.commit()
    session.refresh(poi_type)
    return _type_to_public(poi_type)'''

if "def delete_poi_type_icon(" not in content:
    content = content.replace("@app.get(\"/poi-types/icons/{filename}\")", delete_poi_icon + "\n\n@app.get(\"/poi-types/icons/{filename}\")")

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

with open('frontend/api_client.py', 'r', encoding='utf-8') as f:
    api_content = f.read()

delete_user_icon_api = '''    def delete_user_icon(self, user_id: int) -> dict[str, Any]:
        response = httpx.delete(
            f"{self.api_base}/users/{user_id}/icon",
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()'''

if "def delete_user_icon(" not in api_content:
    api_content = api_content.replace("    def upload_user_icon(", delete_user_icon_api + "\n\n    def upload_user_icon(")

delete_poi_icon_api = '''    def delete_poi_type_icon(self, type_id: int) -> dict[str, Any]:
        response = httpx.delete(
            f"{self.api_base}/poi-types/{type_id}/icon",
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()'''

if "def delete_poi_type_icon(" not in api_content:
    api_content = api_content.replace("    def upload_poi_type_icon(", delete_poi_icon_api + "\n\n    def upload_poi_type_icon(")

with open('frontend/api_client.py', 'w', encoding='utf-8') as f:
    f.write(api_content)

print("Updated backend and api client")
