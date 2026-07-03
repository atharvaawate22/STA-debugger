from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import admin_routes, analysis_routes, auth_routes, keys_routes
from .seed import seed_admin

init_db()
seed_admin()

app = FastAPI(
    title="STA Debugger",
    description="Parses OpenSTA timing reports and diagnoses violations "
                "with a rule-based analysis engine.",
)

# The Vite dev server runs on a different port during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(analysis_routes.router)
app.include_router(admin_routes.router)
app.include_router(keys_routes.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
