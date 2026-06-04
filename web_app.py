# web_app.py
import asyncio
import json
import os
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

import config  # validates GEMINI_API_KEY on import

app = FastAPI(title="Auto Video Generator")

# Prevent concurrent generation jobs
_job_lock = asyncio.Lock()

# ── HTML UI ───────────────────────────────────────────────────────────────────

_HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>视频生成器</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f0f2f5; min-height: 100vh;
      display: flex; align-items: center; justify-content: center; padding: 20px;
    }
    .card {
      background: white; border-radius: 16px; padding: 32px;
      width: 100%; max-width: 640px;
      box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    }
    h1 { font-size: 22px; color: #1a1a1a; margin-bottom: 24px; }
    label { display: block; font-size: 14px; color: #555; margin-bottom: 8px; }
    input {
      width: 100%; border: 1.5px solid #ddd; border-radius: 10px;
      padding: 12px 16px; font-size: 16px; outline: none;
      transition: border-color .2s;
    }
    input:focus { border-color: #4f7bf7; }
    button {
      margin-top: 16px; width: 100%; background: #4f7bf7; color: white;
      border: none; border-radius: 10px; padding: 14px; font-size: 16px;
      cursor: pointer; transition: background .2s;
    }
    button:hover:not(:disabled) { background: #3a63d8; }
    button:disabled { background: #a0b4f7; cursor: not-allowed; }
    .log {
      margin-top: 24px; background: #1e1e1e; border-radius: 10px;
      padding: 16px; min-height: 120px; max-height: 360px;
      overflow-y: auto; display: none;
    }
    .log pre {
      color: #d4d4d4; font-family: "SF Mono", Consolas, monospace;
      font-size: 13px; line-height: 1.6; white-space: pre-wrap;
    }
    .downloads { margin-top: 20px; display: none; }
    .downloads h2 { font-size: 16px; color: #1a1a1a; margin-bottom: 12px; }
    .dl-btn {
      display: inline-block; margin-right: 12px; margin-bottom: 8px;
      padding: 10px 20px; background: #f0f7ee; color: #2d7a4f;
      border: 1.5px solid #b7dfca; border-radius: 8px;
      text-decoration: none; font-size: 14px; font-weight: 500;
      transition: background .2s;
    }
    .dl-btn:hover { background: #dcf0e4; }
    .error-msg {
      margin-top: 16px; padding: 12px 16px; background: #fef2f2;
      color: #dc2626; border-radius: 8px; font-size: 14px; display: none;
    }
  </style>
</head>
<body>
  <div class="card">
    <h1>🎬 英语对话视频生成器</h1>
    <label for="topic">视频主题</label>
    <input id="topic" type="text" placeholder="例如：职场催进度、开会迟到" />
    <button id="btn" onclick="generate()">开始生成</button>
    <div class="error-msg" id="error"></div>
    <div class="log" id="log"><pre id="logText"></pre></div>
    <div class="downloads" id="downloads">
      <h2>✅ 生成完成</h2>
      <a class="dl-btn" id="dlVideo" href="#" download>📥 下载视频</a>
      <a class="dl-btn" id="dlText" href="#" download>📄 下载中英对照</a>
    </div>
  </div>
  <script>
    function generate() {
      const topic = document.getElementById('topic').value.trim();
      if (!topic) { alert('请输入主题'); return; }

      const btn      = document.getElementById('btn');
      const log      = document.getElementById('log');
      const logText  = document.getElementById('logText');
      const downloads = document.getElementById('downloads');
      const error    = document.getElementById('error');

      btn.disabled = true;
      btn.textContent = '生成中…';
      log.style.display = 'block';
      logText.textContent = '';
      downloads.style.display = 'none';
      error.style.display = 'none';

      const es = new EventSource('/generate?topic=' + encodeURIComponent(topic));

      es.addEventListener('log', e => {
        logText.textContent += e.data + '\\n';
        log.scrollTop = log.scrollHeight;
      });

      es.addEventListener('done', e => {
        es.close();
        btn.disabled = false;
        btn.textContent = '开始生成';
        const { video, bilingual } = JSON.parse(e.data);
        document.getElementById('dlVideo').href = video;
        document.getElementById('dlText').href = bilingual;
        downloads.style.display = 'block';
      });

      es.addEventListener('error_msg', e => {
        es.close();
        btn.disabled = false;
        btn.textContent = '重新生成';
        error.textContent = '生成失败：' + e.data;
        error.style.display = 'block';
      });
    }

    document.getElementById('topic').addEventListener('keydown', e => {
      if (e.key === 'Enter') generate();
    });
  </script>
</body>
</html>
"""


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return _HTML


async def _stream_pipeline(topic: str) -> AsyncGenerator[str, None]:
    """Run make_video.py as a subprocess; yield SSE events from its stdout."""
    if _job_lock.locked():
        yield "event: error_msg\ndata: 已有任务正在运行，请稍候再试\n\n"
        return

    async with _job_lock:
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-u", "make_video.py", "--topic", topic,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=Path(__file__).parent,
                # Force unbuffered output so SSE receives each line immediately
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )

            async for raw in proc.stdout:
                line = raw.decode("utf-8", errors="replace").rstrip()
                if line:
                    yield f"event: log\ndata: {line}\n\n"

            await proc.wait()

            if proc.returncode == 0:
                safe_topic = topic.strip().strip("'\"")
                encoded = urllib.parse.quote(safe_topic)
                payload = json.dumps({
                    "video":     f"/output/{encoded}/final.mp4",
                    "bilingual": f"/output/{encoded}/bilingual.txt",
                })
                yield f"event: done\ndata: {payload}\n\n"
            else:
                yield "event: error_msg\ndata: 生成失败，请查看日志\n\n"

        except Exception as exc:
            yield f"event: error_msg\ndata: {exc}\n\n"


@app.get("/generate")
async def generate(topic: str):
    return StreamingResponse(
        _stream_pipeline(topic),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/output/{topic}/{filename}")
async def download(topic: str, filename: str):
    output_root = (Path(__file__).parent / "output").resolve()
    path = (output_root / urllib.parse.unquote(topic) / filename).resolve()
    # Guard against path traversal (e.g. ..%2F..%2Fetc/passwd)
    if not path.is_relative_to(output_root) or not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=filename)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    """Start the server and open the browser after a short delay."""
    threading.Timer(1.2, lambda: webbrowser.open("http://localhost:8000")).start()
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


if __name__ == "__main__":
    main()
