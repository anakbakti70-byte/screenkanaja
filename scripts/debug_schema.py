import os
import psycopg2
from dotenv import load_dotenv
load_dotenv("apps/backend/.env")
DB_URI = os.getenv("SUPABASE_URI_SESSIONPOOLER")
conn = psycopg2.connect(DB_URI)
cur = conn.cursor()
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'users';")
for row in cur.fetchall():
    print(row)
conn.close()
