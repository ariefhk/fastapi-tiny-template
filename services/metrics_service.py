from commons.config import get_configs
from databases.unit_of_work import UnitOfWork


class MetricsService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def get_metrics(self) -> dict:
        """Return basic application metadata."""
        cfg = get_configs()
        return {
            "app_name": cfg.APP_NAME,
            "version": cfg.APP_VERSION,
            "environment": cfg.ENVIRONMENT,
        }
