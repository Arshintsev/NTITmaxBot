class PyrusError(Exception):
    """Базовая ошибка Pyrus"""


class PyrusAuthError(PyrusError):
    """Ошибка авторизации"""


class PyrusNetworkError(PyrusError):
    """Сетевая ошибка"""


class PyrusValidationError(PyrusError):
    """Ошибка данных"""


class PyrusAPIError(PyrusError):
    """Ошибки API"""
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code