from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, stocks, scanner, users, backtest
import asyncio
from contextlib import asynccontextmanager

# Global error handler for database issues
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Background scanner and sync workers are managed externally via start_all.sh
    # This keeps the API lightweight and prevents initialization hangs.
    print("🚀 API: System online and responsive.", flush=True)
    yield
    print("🛑 API: System shutting down.", flush=True)

app = FastAPI(title="Stock Trading Scanner API", lifespan=lifespan)
print("FASTAPI: Application instance created.", flush=True)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    print(f"GLOBAL ERROR: {exc}", flush=True)
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal Server Error",
            "detail": str(exc),
            "trace": traceback.format_exc()
        },
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
