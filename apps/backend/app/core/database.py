from supabase import create_client, Client
from app.core.config import settings

# Use service role key to bypass RLS for backend operations
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY)
