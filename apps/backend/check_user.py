from app.core.database import supabase
from app.core.config import settings

def check():
    print(f"Connecting to: {settings.SUPABASE_URL}")
    res = supabase.table("users").select("*").eq("username", "admin").execute()
    if res.data:
        user = res.data[0]
        print(f"User found: {user['username']}")
        print(f"Hash length: {len(user['hashed_password'])}")
        print(f"Hash starts with: {user['hashed_password'][:10]}")
    else:
        print("User admin not found")

if __name__ == "__main__":
    check()
