from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import router as auth_router
from .config import DASHBOARD_ORIGIN
from .routes import auttaja, polls, templates, utility, warnings

app = FastAPI(title="Vigila Dashboard API", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[DASHBOARD_ORIGIN, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(warnings.router, prefix="/api/warnings", tags=["warnings"])
app.include_router(polls.router, prefix="/api/polls", tags=["polls"])
app.include_router(templates.router, prefix="/api/poll-templates", tags=["templates"])
app.include_router(auttaja.router, prefix="/api/auttaja", tags=["auttaja"])
app.include_router(utility.router, prefix="/api/utility", tags=["utility"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
