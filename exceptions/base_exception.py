from typing import Any


class BaseException(Exception):
    """Base for all application-defined errors."""

    code: str = "INTERNAL_ERROR"
    status_code: int = 500

    def __init__(
        self,
        message: str = "",
        *,
        details: list[Any] | None = None,
    ) -> None:
        super().__init__(message)
        if message:
            self.message = message
        else:
            self.message = self.__class__.__name__
        if details is None:
            self.details: list[Any] = []
        else:
            self.details = details
