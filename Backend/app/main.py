import asyncio
import sys


if sys.platform == "win32":
    import warnings


    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            policy = asyncio.get_event_loop_policy()
            if not isinstance(
                policy, getattr(asyncio, "WindowsProactorEventLoopPolicy", ())
            ):
                asyncio.set_event_loop_policy(
                    asyncio.WindowsProactorEventLoopPolicy()
                )
        except Exception:
            pass


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from app.api.router import api_router
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    description="Backend API for the VeriGate software verification platform.",
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    api_router,
    prefix="/api/v1",
)
@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
def health_check() -> dict[str, str]:
    return {"status": "ok"}
