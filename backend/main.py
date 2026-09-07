import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .database import db_conn, init_db
from .mock_data import seed_database
from .routers import analytics, ingest, actions

app = FastAPI(
    title="CashTrap — SIH 2026",
    description="AI-Powered Cybercrime Predictive Analytics Platform for Withdrawal Forecasting",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- App lifecycle: init + seed database on startup ---
@app.on_event("startup")
def startup_event():
    init_db()
    with db_conn() as conn:
        row = conn.execute("SELECT COUNT(*) as c FROM complaints").fetchone()
        if row["c"] == 0:
            seed_database(conn)
            print("[STARTUP] Database initialized and seeded with CashTrap AI data.")
        else:
            print(f"[STARTUP] Database already initialized with {row['c']} complaints.")

# --- API Routers ---
app.include_router(analytics.router)
app.include_router(ingest.router)
app.include_router(actions.router)

# --- Static frontend serving ---
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

@app.get("/")
async def root():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "CashTrap Backend API running. Frontend index not found at " + index_path}

# Mount static files for CSS/JS
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
