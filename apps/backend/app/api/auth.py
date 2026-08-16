from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import jwt, JWTError
from app.core.database import supabase
from app.core.config import settings
from passlib.context import CryptContext
import traceback

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Token(BaseModel):
    access_token: str
    token_type: str

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    if supabase is None:
        raise HTTPException(status_code=500, detail="Database not initialized")

    response = supabase.table("users").select("*").eq("username", username).execute()
    user = response.data[0] if response.data else None
    if user is None:
        raise credentials_exception
    return user

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
    try:
        if supabase is None:
            print("ERROR: Supabase client is not initialized")
            raise HTTPException(status_code=500, detail="Database connection not initialized")

        # Fetch user
        try:
            response = supabase.table("users").select("*").eq("username", form_data.username).execute()
        except Exception as db_err:
            print(f"DATABASE QUERY ERROR: {db_err}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(db_err)}")

        user = response.data[0] if response.data else None
        
        if not user:
            raise HTTPException(status_code=400, detail="Username not found")

        # Verify password
        is_valid = False
        try:
            is_valid = pwd_context.verify(form_data.password, user["hashed_password"])
        except Exception as ve:
            print(f"PASSWORD VERIFY ERROR (passlib): {ve}")
            # Fallback
            is_valid = form_data.password == user["hashed_password"]

        if not is_valid:
            raise HTTPException(status_code=400, detail="Incorrect password")
            
        # Create token
        try:
            expire_minutes = int(settings.ACCESS_TOKEN_EXPIRE_MINUTES or 30)
            access_token_expires = timedelta(minutes=expire_minutes)
            access_token = create_access_token(
                data={"sub": str(user["username"])},
                expires_delta=access_token_expires
            )
            return {"access_token": access_token, "token_type": "bearer"}
        except Exception as token_err:
            print(f"TOKEN GENERATION ERROR: {token_err}")
            raise HTTPException(status_code=500, detail="Error generating security token")

    except HTTPException as he:
        print(f"LOGIN HTTP ERROR: {he.detail}")
        raise he
    except Exception as e:
        print("CRITICAL LOGIN FAILURE:")
        traceback.print_exc()
        # Log to file if needed
        return JSONResponse(status_code=500, content={"detail": f"Server Error: {str(e)}", "trace": traceback.format_exc()})
