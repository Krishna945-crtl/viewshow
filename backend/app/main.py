import asyncio
import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import admin, auth, bookings, catalog, payments, seats
from app.core.config import get_settings
from app.core.redis import close_redis, get_redis
from app.db.session import dispose_engine, sessionmaker
from app.models import ErrorLog
from app.services.events import hub
from app.services.storage import PUBLIC_PREFIX, get_storage
from app.services.sweeper import run_forever

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("cineverse")


@asynccontextmanager
async def lifespan(app: FastAPI):
    hub.start()
    sweeper = asyncio.create_task(run_forever()) if get_settings().run_sweeper else None
    yield
    if sweeper:
        sweeper.cancel()
    await hub.stop()
    await close_redis()
    await dispose_engine()


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title=s.app_name, version="1.0.0", lifespan=lifespan,
                  docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_list, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        rid = request.headers.get("x-request-id") or secrets.token_hex(8)
        request.state.request_id = rid
        try:
            response = await call_next(request)
        except Exception as exc:  # anything unhandled lands in the admin error log
            log.exception("unhandled error %s %s", request.method, request.url.path)
            try:
                async with sessionmaker()() as db:
                    db.add(ErrorLog(request_id=rid, path=request.url.path[:300], method=request.method,
                                    error_type=type(exc).__name__, message=str(exc)[:4000]))
                    await db.commit()
            except Exception:
                log.exception("could not persist error log")
            response = JSONResponse(status_code=500, content={"detail": {
                "code": "server_error", "message": "Something went wrong on our side", "request_id": rid}})
        response.headers["x-request-id"] = rid
        return response

    @app.exception_handler(RequestValidationError)
    async def validation(_: Request, exc: RequestValidationError):
        errs = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": {"code": "invalid", "message": errs[0]["message"]
                                                                 if errs else "Invalid input", "errors": errs}})

    for r in (auth.router, catalog.router, seats.router, bookings.router, payments.router, admin.router):
        app.include_router(r, prefix="/api")

    # uploaded posters. behind a CDN / bucket in production, plain files locally
    app.mount(PUBLIC_PREFIX, StaticFiles(directory=get_storage().root), name="media")

    @app.get("/api/health")
    async def health():
        await get_redis().ping()
        return {"ok": True}

    return app


app = create_app()
