from .exceptions import (
    PyrusAuthError,
    PyrusNetworkError,
    PyrusValidationError,
    PyrusAPIError,
)


def map_http_error(status_code: int, message: str):
    if status_code == 401:
        return PyrusAuthError("Unauthorized access to Pyrus API")

    if status_code == 400:
        return PyrusValidationError(message)

    if status_code >= 500:
        return PyrusAPIError("Pyrus server error", status_code)

    return PyrusAPIError(message, status_code)

