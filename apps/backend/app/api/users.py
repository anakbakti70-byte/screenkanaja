from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.core.database import supabase
from passlib.context import CryptContext
from .auth import get_current_user
import bcrypt
import os
import shutil

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

class UserSettingsUpdate(BaseModel):
    username: str | None = None
    password: str | None = None

def get_avatar_path(username: str):
    return os.path.join(UPLOAD_DIR, f"{username}_avatar.jpg")

@router.get("/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    username = current_user["username"]
    avatar_url = None
    if os.path.exists(get_avatar_path(username)):
        avatar_url = f"/api/users/avatar/{username}?t={os.path.getmtime(get_avatar_path(username))}"
        
    return {
        "id": current_user["id"],
        "username": username,
        "role": current_user["role"],
        "balance": current_user.get("balance", 0),
        "avatar_url": avatar_url
    }
    
@router.get("/avatar/{username}")
async def get_avatar(username: str):
    filepath = get_avatar_path(username)
    if os.path.exists(filepath):
        return FileResponse(filepath)
    raise HTTPException(status_code=404, detail="Avatar not found")

@router.post("/avatar")
async def upload_avatar(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    username = current_user["username"]
    filepath = get_avatar_path(username)
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"message": "Avatar uploaded successfully", "avatar_url": f"/api/users/avatar/{username}?t={os.path.getmtime(filepath)}"}

@router.put("/settings")
async def update_settings(update_data: UserSettingsUpdate, current_user: dict = Depends(get_current_user)):
    updates = {}
        
    if update_data.username is not None:
        # Check if new username already exists
        if update_data.username != current_user["username"]:
            check = supabase.table("users").select("id").eq("username", update_data.username).execute()
            if check.data:
                raise HTTPException(status_code=400, detail="Username already taken")
            updates["username"] = update_data.username
            
            # Rename avatar if exists
            old_avatar = get_avatar_path(current_user["username"])
            new_avatar = get_avatar_path(update_data.username)
            if os.path.exists(old_avatar):
                os.rename(old_avatar, new_avatar)

    if update_data.password is not None:
        try:
            hashed_password = bcrypt.hashpw(update_data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            updates["hashed_password"] = hashed_password
        except Exception as e:
            # Fallback for passlib
            hashed_password = pwd_context.hash(update_data.password)
            updates["hashed_password"] = hashed_password

    if not updates:
        return {"message": "Tidak ada perubahan (profil/password)"}

    response = supabase.table("users").update(updates).eq("id", current_user["id"]).execute()
    
    return {"message": "Settings updated successfully"}
