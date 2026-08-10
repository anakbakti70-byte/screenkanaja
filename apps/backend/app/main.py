from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, stocks, scanner, users, backtest
import asyncio
from contextlib import asynccontextmanager
from app.scanner.engine import ScannerEngine

# Global error handler for database issues
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background scanner only if possible
    try:
        engine = ScannerEngine()
        task = asyncio.create_task(scheduled_scanner(engine))
        yield
        task.cancel()
    except Exception as e:
        print(f"LIFESPAN ERROR: {e}")
        yield

async def scheduled_scanner(engine):
    """
    Background task to run scanner automatically every 15 minutes.
    """
    while True:
        try:
            # Check if tables exist first
            print("AUTO-SCAN: Starting periodic market scan...")
            await engine.run_scan(market="idx", timeframe="1d")
            print("AUTO-SCAN: Finished.")
        except Exception as e:
            print(f"AUTO-SCAN ERROR: {e}")
        
        await asyncio.sleep(900)

app = FastAPI(title="Stock Trading Scanner API", lifespan=lifespan)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"GLOBAL ERROR: {exc}")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )

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
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "Stock Trading Scanner API is running"}
