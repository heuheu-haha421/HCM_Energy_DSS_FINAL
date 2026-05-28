from typing import Generic, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    code   : str
    data   : T | None = None


def success_response(message: str, code: str, data=None):
    return {
        "success": True,
        "message": message,
        "code"   : code,
        "data"   : data,
    }
