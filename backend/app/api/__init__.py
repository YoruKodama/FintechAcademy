"""HTTP-слой: методы API и формат ошибок."""

from .errors import ApiError, install_error_handlers
from .routes import router

__all__ = ["ApiError", "install_error_handlers", "router"]
