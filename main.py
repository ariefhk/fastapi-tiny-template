import uvicorn
from fastapi import FastAPI

from commons.config import get_configs
from commons.lifespan import lifespan
from exceptions.registry import register_exceptions
from loggers.registry import register_logging
from middlewares import register_middlewares
from routers.router import common_router
from routers.v1.router import v1_router

register_logging()


def create_app() -> FastAPI:
    cfg = get_configs()
    is_dev = cfg.ENVIRONMENT == "dev"

    app = FastAPI(
        title=cfg.APP_NAME,
        version=cfg.APP_VERSION,
        docs_url="/docs" if is_dev else None,
        redoc_url="/redoc" if is_dev else None,
        lifespan=lifespan,
        swagger_ui_parameters={"persistAuthorization": True},
    )

    register_middlewares(app)
    register_exceptions(app)

    app.include_router(common_router)
    app.include_router(v1_router)

    return app


app = create_app()

if __name__ == "__main__":
    cfg = get_configs()
    is_dev = cfg.ENVIRONMENT == "dev"

    if is_dev:
        uvicorn.run(
            "main:app",
            host=cfg.HOST,
            port=cfg.PORT,
            timeout_keep_alive=cfg.KEEP_ALIVE,
            workers=cfg.WORKERS,
            reload=True,
            log_level="debug",
            loop="uvloop",
            http="httptools",
            limit_concurrency=cfg.LIMIT_CONCURRENCY,
            backlog=2048,
            access_log=True,
        )
    else:
        uvicorn.run(
            "main:app",
            host=cfg.HOST,
            port=cfg.PORT,
            timeout_keep_alive=cfg.KEEP_ALIVE,
            workers=cfg.WORKERS,
            log_level="info",
            loop="uvloop",
            http="httptools",
            limit_concurrency=cfg.LIMIT_CONCURRENCY,
            backlog=2048,
            access_log=False,
        )
