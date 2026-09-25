"""V2HTML 服务端 · FastAPI 应用（前台 API + 管理后台）。

  启动:  uvicorn server.app:app --host 127.0.0.1 --port 8410
  前台:  /                       提交页
         /api/jobs  /api/jobs/{id}  /api/health
         /output/<video_id>/…     产物（slides.html / doc.md / frames）
  管理:  /admin                  仪表盘（需登录）
         /admin/jobs[/id]        任务管理与重试/推送/删除
         /admin/config           LLM / 推送 / 密码配置
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import pathlib
import re
import shutil
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bin"))
import v2h  # noqa: E402  复用客户端素材管线（fetch/transcribe/frames）

from server import auth, generate, llm, pushof, store  # noqa: E402
from server.admin import router as admin_router  # noqa: E402

OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

app = FastAPI(title="V2HTML Server", version="0.2.0", redirect_slashes=False)
app.include_router(admin_router)


@app.middleware("http")
async def no_cache_middleware(request, call_next):
    """产物是动态的：禁止 Cloudflare 等缓存层缓存任何响应。"""
    resp = await call_next(request)
    resp.headers["Cache-Control"] = "no-store"
    return resp


EXEC = ThreadPoolExecutor(max_workers=int(os.environ.get("V2HTML_WORKERS", "1")))
JOBS: dict[str, dict] = {}
LOCK = threading.Lock()

THEMES = ["science", "tutorial", "commentary", "terracotta", "paper-doc", "prism",
          "aurora", "glass", "memphis", "vapor", "riso", "broadsheet", "luxe",
          "academia", "y2k", "blueprint", "pop", "zen", "swiss", "bauhaus",
          "deco", "brutal", "kraft", "neon", "geist", "carbon", "ant",
          "tdesign", "arco", "material3"]


def _log(job: dict, msg: str) -> None:
    job["steps"].append({"t": round(time.time() - job["t0"], 1), "msg": msg})


def _authed(request: Request, authorization: str) -> bool:
    """会话 Cookie（后台）或 Bearer Token（外部调用）任一通过即可。"""
    if auth.check_session(request.cookies.get("v2h_session")):
        return True
    token = os.environ.get("V2HTML_TOKEN", "")
    return bool(token) and authorization == f"Bearer {token}"


def _require(request: Request, authorization: str) -> None:
    token = os.environ.get("V2HTML_TOKEN", "")
    if not _authed(request, authorization) and token:
        raise HTTPException(401, "需要登录或 Bearer Token")


def _run_job(job: dict) -> None:
    try:
        job["status"] = "running"
        before = {p.name for p in OUT.glob("*") if p.is_dir()}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = v2h.fetch(job["url"], job["max_frames"], do_frames=True)
        if rc != 0:
            raise RuntimeError("素材抓取失败（yt-dlp），详见服务端日志")
        new = {p.name for p in OUT.glob("*") if p.is_dir()} - before
        if new:
            vid = sorted(new)[-1]
        else:
            m = re.search(r'"id":\s*"([\w-]+)"', buf.getvalue())
            if not m:
                raise RuntimeError("无法定位产物目录")
            vid = m.group(1)
        job["video_id"] = vid
        workdir = OUT / vid
        _log(job, f"素材就绪 → {vid}（{job['max_frames']} 帧）")

        if not (workdir / "transcript.md").exists():
            _log(job, "无字幕，尝试本地 Whisper 兜底…")
            if v2h.transcribe(vid) != 0:
                raise RuntimeError("无字幕且无可用 Whisper（需安装 mlx-whisper/openai-whisper）")

        if not llm.available():
            job["status"] = "paused_no_llm"
            _log(job, "素材与转写已就绪；请在管理后台「系统配置」填写 LLM API Key")
            return

        meta = v2h.describe(workdir)
        transcript_md = (workdir / "transcript.md").read_text(encoding="utf-8")

        _log(job, "LLM：类型判定…")
        dtype = job["doc_type"]
        if dtype == "auto":
            dtype = generate.classify(meta, transcript_md)
            _log(job, f"判定类型：{dtype}")
        job["doc_type"] = dtype

        _log(job, f"LLM：撰写 {dtype} 文档…")
        sheet = workdir / "sheet.jpg"
        doc_md = generate.gen_doc(dtype, meta, transcript_md,
                                  sheet if store.load()["llm"].get("vision") else None)
        (workdir / "doc.md").write_text(doc_md, encoding="utf-8")

        _log(job, "LLM：编排幻灯片…")
        frames = json.loads((workdir / "frames.json").read_text(encoding="utf-8"))
        have = {f["file"] for f in frames}
        fragment = generate.gen_slides(dtype, doc_md, frames, have)
        title = meta.get("title") or vid
        job["title"] = title
        theme = job["theme"]
        if theme == "auto":
            theme = {"tutorial": "tutorial", "science": "science",
                     "commentary": "commentary"}.get(dtype, "geist")
        (workdir / "slides.html").write_text(
            generate.build_deck(fragment, title, theme), encoding="utf-8")
        _log(job, f"完成：doc.md + slides.html（主题 {theme}）")
        job["status"] = "done"

        push_cfg = store.load()["push"]
        if push_cfg.get("enabled"):
            try:
                _log(job, "推送到 openflow…")
                result = pushof.push(workdir, meta, doc_md)
                job["pushed"] = result
                _log(job, f"已推送 openflow：{result['status']} · {result['slug']}")
            except Exception as exc:  # noqa: BLE001  推送失败不影响任务
                _log(job, f"推送失败：{exc}")
    except Exception as exc:  # noqa: BLE001  任务级兜底
        job["status"] = "error"
        job["error"] = str(exc)
        _log(job, f"失败：{exc}")


# -------------------------------------------------------------- 操作函数 ----

def retry_job(jid: str) -> None:
    job = JOBS.get(jid)
    if not job:
        raise HTTPException(404, "no such job")
    job.update(status="queued", steps=[], error=None, pushed=None)
    EXEC.submit(_run_job, job)


def delete_job(jid: str) -> None:
    job = JOBS.pop(jid, None)
    if not job:
        raise HTTPException(404, "no such job")
    if job.get("video_id"):
        shutil.rmtree(OUT / job["video_id"], ignore_errors=True)


def push_job(jid: str) -> dict:
    job = JOBS.get(jid)
    if not job or not job.get("video_id"):
        raise HTTPException(404, "job/materials not found")
    workdir = OUT / job["video_id"]
    doc = workdir / "doc.md"
    if not doc.exists():
        raise HTTPException(400, "doc.md 尚未生成")
    meta = v2h.describe(workdir)
    meta["url"] = job["url"]
    return pushof.push(workdir, meta, doc.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ 路由 ----

@app.post("/api/jobs")
async def create_job(body: dict, request: Request,
                     authorization: str = Header(default="")):
    _require(request, authorization)
    url = str(body.get("url", "")).strip()
    if not re.match(r"^https?://", url):
        raise HTTPException(400, "url 必须是 http(s) 链接")
    theme = body.get("theme") or "auto"
    if theme != "auto" and theme not in THEMES:
        raise HTTPException(400, f"未知主题，可选：{', '.join(THEMES)} 或 auto")
    job = {
        "id": uuid.uuid4().hex[:12], "url": url,
        "doc_type": body.get("doc_type") or "auto",
        "theme": theme, "max_frames": int(body.get("max_frames") or 24),
        "status": "queued", "steps": [], "video_id": None,
        "title": None, "pushed": None, "error": None,
        "t0": time.time(), "created": time.strftime("%m-%d %H:%M"),
    }
    with LOCK:
        JOBS[job["id"]] = job
    EXEC.submit(_run_job, job)
    return {"id": job["id"]}


@app.get("/api/jobs")
def list_jobs(request: Request, authorization: str = Header(default="")):
    _require(request, authorization)
    return [_job_brief(j) for j in sorted(JOBS.values(), key=lambda x: x["t0"], reverse=True)]


def _job_brief(j: dict) -> dict:
    return {"id": j["id"], "url": j["url"], "status": j["status"],
            "video_id": j["video_id"], "doc_type": j["doc_type"], "theme": j["theme"],
            "title": j.get("title"), "error": j["error"], "created": j["created"]}


@app.get("/api/jobs/{jid}")
def job_detail(jid: str, request: Request, authorization: str = Header(default="")):
    _require(request, authorization)
    job = JOBS.get(jid)
    if not job:
        raise HTTPException(404, "no such job")
    vid = job["video_id"]
    base = f"output/{vid}" if vid else None
    return {**{k: job[k] for k in ("id", "url", "status", "steps", "video_id",
                                   "doc_type", "theme", "title", "error", "pushed")},
            "artifacts": {
                "slides": f"{base}/slides.html" if vid else None,
                "doc": f"api/jobs/{jid}/doc" if vid else None,
                "transcript": f"{base}/transcript.md" if vid else None,
                "sheet": f"{base}/sheet.jpg" if vid else None,
            }}


@app.get("/api/jobs/{jid}/doc")
def job_doc(jid: str):
    job = JOBS.get(jid)
    if not job or not job["video_id"]:
        raise HTTPException(404, "no such job")
    p = OUT / job["video_id"] / "doc.md"
    if not p.exists():
        raise HTTPException(404, "doc not generated")
    return PlainTextResponse(p.read_text(encoding="utf-8"),
                             media_type="text/plain; charset=utf-8")


@app.post("/api/jobs/{jid}/retry")
def api_retry(jid: str, request: Request, authorization: str = Header(default="")):
    _require(request, authorization)
    retry_job(jid)
    return {"ok": True}


@app.post("/api/jobs/{jid}/push")
def api_push(jid: str, request: Request, authorization: str = Header(default="")):
    _require(request, authorization)
    return push_job(jid)


@app.post("/api/jobs/{jid}/delete")
def api_delete(jid: str, request: Request, authorization: str = Header(default="")):
    _require(request, authorization)
    delete_job(jid)
    return {"ok": True}


@app.get("/api/config")
def api_config(request: Request, authorization: str = Header(default="")):
    _require(request, authorization)
    cfg = store.load()
    out = json.loads(json.dumps(cfg))            # 深拷贝
    if out.get("llm", {}).get("api_key"):
        out["llm"]["api_key"] = out["llm"]["api_key"][:6] + "***"
    return out


@app.post("/api/config")
async def api_config_set(section: str, body: dict, request: Request,
                         authorization: str = Header(default="")):
    _require(request, authorization)
    if section not in ("llm", "push"):
        raise HTTPException(400, "section 必须是 llm 或 push")
    cfg = store.update(section, body)
    return {section: cfg[section]}


@app.get("/api/health")
def health():
    cfg = store.load()
    return {**llm.info(), "proxy": v2h.detect_proxy(), "auth": bool(os.environ.get("V2HTML_TOKEN")),
            "push_enabled": bool(cfg["push"].get("enabled")),
            "push_status": cfg["push"].get("status"),
            "output": str(OUT), "themes": len(THEMES)}


@app.get("/")
def index():
    return FileResponse(ROOT / "server" / "static" / "index.html")


app.mount("/output", StaticFiles(directory=OUT), name="output")
