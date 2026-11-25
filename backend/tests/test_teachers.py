import pytest
import uuid
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_teachers_crud_and_pagination(async_client: AsyncClient, auth_headers: dict):
    # 1. List teachers with pagination
    res = await async_client.get("/teachers?page=1&per_page=10", headers=auth_headers)
    assert res.status_code == 200
    res_json = res.json()
    assert "data" in res_json
    assert "total" in res_json
    assert "page" in res_json

    # 2. Create teacher
    teacher_name = f"Test Teacher {uuid.uuid4().hex[:6]}"
    create_res = await async_client.post(
        "/teachers",
        headers=auth_headers,
        json={
            "full_name": teacher_name,
            "primary_subject": "Matematika",
            "max_weekly_hours": 20,
            "max_daily_hours": 4
        }
    )
    assert create_res.status_code == 201
    created_teacher = create_res.json()
    teacher_id = created_teacher["id"]
    assert created_teacher["full_name"] == teacher_name

    # 3. Search teacher
    search_res = await async_client.get(f"/teachers?search={teacher_name}", headers=auth_headers)
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert len(search_data["data"]) >= 1

    # 4. Update teacher
    update_res = await async_client.put(
        f"/teachers/{teacher_id}",
        headers=auth_headers,
        json={"max_weekly_hours": 24}
    )
    assert update_res.status_code == 200
    assert update_res.json()["max_weekly_hours"] == 24

    # 5. Delete teacher
    del_res = await async_client.delete(f"/teachers/{teacher_id}", headers=auth_headers)
    assert del_res.status_code == 200

    # 6. Verify 404 on deleting again
    del_404_res = await async_client.delete(f"/teachers/{teacher_id}", headers=auth_headers)
    assert del_404_res.status_code == 404
