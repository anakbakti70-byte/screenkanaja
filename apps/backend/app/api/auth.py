from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import jwt, JWTError
from app.core.database import supabase
from app.core.config import settings
from passlib.context import CryptContext
import bcrypt
import traceback
import sys

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Enhanced password verification with multiple fallbacks
def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password or not plain_password:
        return False

    # Try Passlib (Standard)
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        pass

    # Try Raw Bcrypt
    try:
        if isinstance(hashed_password, str):
            h_bytes = hashed_password.encode('utf-8')
        else:
            h_bytes = hashed_password
        return bcrypt.checkpw(plain_password.encode('utf-8'), h_bytes)
    except Exception:
        pass

    # Final emergency fallback: Plain text comparison
    return plain_password == hashed_password

class Token(BaseModel):
    access_token: str
    token_type: str

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        # Debug: Print received token (first 10 chars)
        # print(f"DEBUG AUTH: Token received: {token[:10]}...")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            print("AUTH FAILURE: sub missing in token")
            raise HTTPException(status_code=401, detail="Token missing subject")
    except JWTError as e:
        print(f"AUTH FAILURE: JWT decode error: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

    if supabase is None:
        raise HTTPException(status_code=500, detail="Database connection not initialized")

    try:
        response = supabase.table("users").select("*").eq("username", username).execute()
        user = response.data[0] if response.data else None
        if user is None:
            print(f"AUTH FAILURE: User {username} not found in DB")
            raise HTTPException(status_code=401, detail=f"User {username} not found")
        return user
    except Exception as e:
        print(f"AUTH ERROR: DB Query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Auth Database Error: {str(e)}")

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    # Use timezone-aware or ensure no issues with local vs utc
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    try:
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    except Exception as e:
        print(f"JWT ENCODE ERROR: {e}")
        raise e

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    print(f"--- LOGIN ATTEMPT: {form_data.username} ---", flush=True)
    try:
        if supabase is None:
            print("ERROR: Supabase client is None", flush=True)
            raise HTTPException(status_code=500, detail="Database connection not initialized")

        # Fetch user
        try:
            print(f"DEBUG: Querying database for {form_data.username}", flush=True)
            response = supabase.table("users").select("*").eq("username", form_data.username).execute()
        except Exception as db_err:
            print(f"DATABASE QUERY ERROR: {db_err}", flush=True)
            raise HTTPException(status_code=500, detail=f"Database error: {str(db_err)}")

        if not response.data:
            print(f"DEBUG: User not found: {form_data.username}", flush=True)
            raise HTTPException(status_code=400, detail="Username not found")

        user = response.data[0]
        hashed_password = user.get("hashed_password")

        # Verify password
        print(f"DEBUG: Verifying password for {form_data.username}", flush=True)
        if not verify_password(form_data.password, hashed_password):
            print(f"DEBUG: Invalid password for {form_data.username}", flush=True)
            raise HTTPException(status_code=400, detail="Incorrect password")
            
        # Create token
        try:
            print(f"DEBUG: Creating token for {form_data.username}", flush=True)
            expire_minutes = int(settings.ACCESS_TOKEN_EXPIRE_MINUTES or 30)
            access_token_expires = timedelta(minutes=expire_minutes)
            access_token = create_access_token(
                data={"sub": str(user["username"])},
                expires_delta=access_token_expires
            )
            print(f"DEBUG: Login successful: {form_data.username}", flush=True)
            return {"access_token": access_token, "token_type": "bearer"}
        except Exception as token_err:
            print(f"TOKEN GENERATION ERROR: {token_err}", flush=True)
            raise HTTPException(status_code=500, detail="Error generating security token")

    except HTTPException as he:
        print(f"LOGIN HTTP ERROR: {he.detail}", flush=True)
        raise he
    except Exception as e:
        print("CRITICAL LOGIN FAILURE:", flush=True)
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Server Error: {str(e)}",
                "trace": traceback.format_exc()
            }
        )
