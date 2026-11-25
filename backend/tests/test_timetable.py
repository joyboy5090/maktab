import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_timetable_endpoints(async_client: AsyncClient, auth_headers: dict):
    # Test timetable retrieval
    res = await async_client.get("/timetable/all?term=1&per_page=50", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "data" in data

    # Test timetable generator endpoint
    gen_res = await async_client.post(
        "/timetable/generate",
        headers=auth_headers,
        json={"term": 1, "slots_per_day": 6}
    )
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    assert "total_lessons_scheduled" in gen_data
    assert gen_data["success"] is True
