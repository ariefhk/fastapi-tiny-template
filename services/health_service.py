from sqlalchemy import text

from databases.unit_of_work import UnitOfWork


class HealthService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def get_status(self) -> dict:
        """Ping the database and return a status summary."""
        try:
            await self.uow.session.execute(text("SELECT 1"))
            db_status = "ok"
        except Exception:
            db_status = "error"

        return {"status": "ok", "database": db_status}
