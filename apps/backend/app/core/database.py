from supabase import create_client, Client
from app.core.config import settings
import sys

# Use service role key to bypass RLS for backend operations
supabase: Client = None

try:
    if not settings.SUPABASE_URL or "your-project" in settings.SUPABASE_URL:
        print("CRITICAL: Supabase URL is missing or placeholder.")
    else:
        print(f"DEBUG: Initializing Supabase client with URL: {settings.SUPABASE_URL}")
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY)
        print("DEBUG: Supabase client initialized successfully.")
except Exception as e:
    print(f"ERROR: Could not initialize Supabase client: {e}", file=sys.stderr)
    supabase = None
