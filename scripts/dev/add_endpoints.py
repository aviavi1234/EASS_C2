import sys

with open('backend/main.py', 'a', encoding='utf-8') as f:
    f.write('''

@app.get("/units/", response_model=List[UserPublic])
def list_active_units(
    session: Session = Depends(db.get_session),
    _: User = Depends(get_current_user),
):
    users = session.exec(select(User).where(User.show_location == True)).all()
    return [_user_to_public(u) for u in users]


@app.post("/users/{user_id}/icon", response_model=UserPublic)
async def upload_user_unit_icon(
    user_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(db.get_session),
    current_user: User = Depends(get_current_user),
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this user")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_ICON_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type. Allowed: {', '.join(sorted(ALLOWED_ICON_SUFFIXES))}",
        )
    new_name = f"user_{user_id}_{uuid.uuid4().hex}{suffix}"
    dest = user_icons_directory() / new_name
    data = await file.read()
    if len(data) > 2_000_000:
        raise HTTPException(status_code=400, detail="File too large (max 2 MB)")
    dest.write_bytes(data)
    
    if user.unit_icon_filename and safe_icon_basename(user.unit_icon_filename):
        old = user_icons_directory() / user.unit_icon_filename
        if old.is_file() and old.name != new_name:
            old.unlink()
            
    user.unit_icon_filename = new_name
    session.add(user)
    session.commit()
    session.refresh(user)
    return _user_to_public(user)


@app.get("/users/icons/{filename}")
def get_user_unit_icon(filename: str):
    if not safe_icon_basename(filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = user_icons_directory() / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Icon not found")
    return FileResponse(path)
''')
    print("Appended unit endpoints to backend/main.py")
