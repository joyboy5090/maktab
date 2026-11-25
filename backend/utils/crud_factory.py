"""
Umumiy CRUD Factory yordamchisi (Maktab SMS)
Standartlashtirilgan CRUD operatsiyalari va javob formatlari.
"""
from typing import Type, TypeVar, Optional, List, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status
from pydantic import BaseModel

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

def success_response(data: Any, message: Optional[str] = None) -> Dict[str, Any]:
    """Standart muvaffaqiyatli API javobi"""
    res: Dict[str, Any] = {"success": True, "data": data}
    if message:
        res["message"] = message
    return res

def error_response(code: str, message: str) -> Dict[str, Any]:
    """Standart xatolik API javobi"""
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message
        }
    }

def paginate_response(data: List[Any], total: int, page: int, per_page: int) -> Dict[str, Any]:
    """Standart sahifalangan javob formati"""
    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 1
    return {
        "success": True,
        "data": data,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    }
