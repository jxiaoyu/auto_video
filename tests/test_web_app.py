# tests/test_web_app.py
from httpx import AsyncClient, ASGITransport


async def test_index_returns_html():
    from web_app import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "视频生成器" in resp.text


async def test_download_missing_file_returns_404():
    from web_app import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/output/nonexistent_topic/final.mp4")
    assert resp.status_code == 404


async def test_generate_rejects_concurrent_jobs(monkeypatch):
    """While a job is running, a second /generate call returns error_msg SSE event."""
    import asyncio
    import web_app

    # Simulate a job already holding the lock
    await web_app._job_lock.acquire()
    try:
        from web_app import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/generate?topic=test")
    finally:
        web_app._job_lock.release()

    assert resp.status_code == 200  # SSE always returns 200; errors are sent as events
    assert "error_msg" in resp.text
    assert "已有任务" in resp.text
