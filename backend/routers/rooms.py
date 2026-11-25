from typing import Optional
from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from database.connection import get_tenant_db
from database.models import Room
from schemas.schemas import RoomCreate, RoomResponse, RoomUpdate
from core.rbac import CurrentUser, require_school_admin, require_any_authenticated
from utils.crud_factory import paginate_response

router = APIRouter(prefix="/rooms", tags=["Xonalar Moduli"])

@router.get("")
async def list_rooms(
    page: int = Query(1, ge=1, description="Sahifa raqami"),
    per_page: int = Query(50, ge=1, le=100, description="Har bir sahifadagi elementlar"),
    search: Optional[str] = Query(None, description="Xona raqami yoki nomi bo'yicha qidiruv"),
    type: Optional[str] = Query(None, description="Xona turi bo'yicha filtr (GENERAL, LABORATORY, GYM...)"),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_any_authenticated)
):
    query = select(Room).where(Room.school_id == current_user.school_id)

    if search:
        query = query.where(
            or_(
                Room.room_number.ilike(f"%{search.strip()}%"),
                Room.name.ilike(f"%{search.strip()}%")
            )
        )
    if type:
        query = query.where(Room.room_type.ilike(f"%{type.strip()}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    query = query.order_by(Room.room_number).offset((page - 1) * per_page).limit(per_page)
    res = await db.execute(query)
    rooms = res.scalars().all()

    data = [
        {
            "id": r.id,
            "school_id": r.school_id,
            "room_number": r.room_number,
            "name": r.name,
            "capacity": r.capacity,
            "room_type": r.room_type,
        }
        for r in rooms
    ]

    return paginate_response(data, total, page, per_page)

@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    data: RoomCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_school_admin)
):
    new_room = Room(
        school_id=current_user.school_id,
        room_number=data.room_number,
        name=data.name,
        capacity=data.capacity,
        room_type=data.room_type
    )
    db.add(new_room)
    await db.commit()
    await db.refresh(new_room)
    return new_room

@router.put("/{room_id}", response_model=RoomResponse)
async def update_room(
    room_id: str,
    data: RoomUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_school_admin)
):
    query = select(Room).where(Room.id == room_id, Room.school_id == current_user.school_id)
    res = await db.execute(query)
    room = res.scalar_one_or_none()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Xona topilmadi"
        )

    if data.room_number is not None:
        room.room_number = data.room_number
    if data.name is not None:
        room.name = data.name
    if data.capacity is not None:
        room.capacity = data.capacity
    if data.room_type is not None:
        room.room_type = data.room_type

    await db.commit()
    await db.refresh(room)
    return room

@router.delete("/{room_id}", status_code=status.HTTP_200_OK)
async def delete_room(
    room_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_school_admin)
):
    query = select(Room).where(Room.id == room_id, Room.school_id == current_user.school_id)
    res = await db.execute(query)
    room = res.scalar_one_or_none()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="O'chirish uchun xona topilmadi"
        )

    await db.delete(room)
    await db.commit()
    return {"success": True, "message": "Xona bazadan o'chirildi"}
