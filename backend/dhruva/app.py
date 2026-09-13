"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dhruva.api.health import router as health_router
from dhruva.api.query import router as query_router

ADVISORY_NOTICE = "Advisory only. Follow official INCOIS and IMD warnings."


def create_app() -> FastAPI:
    app = FastAPI(
        title="DHRUVA",
        description=(
            "Deep-sea Hazard, Routing & Understanding via Vernacular Agents. "
            f"ISRO PS 26176. {ADVISORY_NOTICE}"
        ),
        version="0.1.0",
    )
    # The Vite dev server (frontend, Phase 5) runs on a different origin —
    # this is a local demo laptop, not a public deployment, so a permissive
    # localhost allowlist is the right amount of caution, not the maximum.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(query_router)
    return app


app = create_app()
