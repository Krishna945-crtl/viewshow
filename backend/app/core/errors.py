from fastapi import HTTPException


class AppError(HTTPException):
    def __init__(self, status: int, code: str, message: str, extra: dict | None = None):
        super().__init__(status_code=status, detail={"code": code, "message": message, **(extra or {})})


def not_found(what: str) -> AppError:
    return AppError(404, "not_found", f"{what} not found")


def conflict(code: str, message: str, **extra) -> AppError:
    return AppError(409, code, message, extra)


def bad_request(code: str, message: str, **extra) -> AppError:
    return AppError(400, code, message, extra)
