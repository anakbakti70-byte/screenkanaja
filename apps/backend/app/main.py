from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, stocks, scanner, users
import asyncio
from contextlib import asynccontextmanager
from app.scanner.engine import ScannerEngine

engine = ScannerEngine()

async def scheduled_scanner():
    """
    Background task to run scanner automatically every 15 minutes.
    """
    while True:
        try:
            print("AUTO-SCAN: Starting periodic market scan...")
            # Run scan for IDX and US in background
            await engine.run_scan(market="idx", timeframe="15m")
            await engine.run_scan(market="idx", timeframe="1h")
            await engine.run_scan(market="idx", timeframe="1d")
            print("AUTO-SCAN: Finished. Waiting for next cycle.")
        except Exception as e:
            print(f"AUTO-SCAN ERROR: {e}")
        
        # Wait for 15 minutes
        await asyncio.sleep(900)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background scanner
    task = asyncio.create_task(scheduled_scanner())
    yield
    # Cleanup
    task.cancel()

app = FastAPI(title="Stock Trading Scanner API", lifespan=lifespan)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(stocks.router, prefix="/api/stocks", tags=["stocks"])
app.include_router(scanner.router, prefix="/api/scanner", tags=["scanner"])
app.include_router(users.router, prefix="/api/users", tags=["users"])

@app.get("/")
async def root():
    return {"message": "Stock Trading Scanner API is running"}
