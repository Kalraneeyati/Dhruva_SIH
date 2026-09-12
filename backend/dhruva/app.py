"""FastAPI application factory."""

from fastapi import FastAPI

from dhruva.api.health import router as health_router

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
    app.include_router(health_router)
    return app


app = create_app()
