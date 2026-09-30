"""ConFlow 服务端 · 推送适配器层：任务产物按 cfg["push"]["target"] 送达不同目标。

  openflow   OpenFlow 内容库（server/pushof.py，矩阵内容供给端，幂等覆盖）
  wordpress  WordPress REST API（wp-json/wp/v2/posts，应用密码认证；每次推送新建草稿）
  static     渲染为自包含 HTML 落到本地目录（任意静态站 / Nginx 直接挂）
  webhook    成品打包 JSON POST 到任意 URL（n8n / Make / 自建流水线）

新增目标 = 实现一个 `push_xxx(workdir, meta, doc_md, cfg) -> dict` 并注册进
ADAPTERS（返回 dict 至少含 id / slug / status / target），这就是官方参考插件。
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import re
import time
import urllib.request

import markdown as md_lib

from engine import plugins
from . import pushof, store


# ---------------------------------------------------------------- 共用 ----

def _slide_base() -> str:
    return os.environ.get("CONFLOW_PUBLIC_BASE") or \
        os.environ.get("V2HTML_PUBLIC_BASE") or "/VTH"


def _md2html(doc_md: str) -> str:
    return md_lib.markdown(doc_md, extensions=["extra", "toc"])


def _excerpt(html: str, limit: int = 120) -> str:
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _source_header(meta: dict, vid: str) -> str:
    """来源署名条：原视频链接 + 配套幻灯片，各适配器共用。"""
    video_url = meta.get("url") or ""
    slide_url = f"{_slide_base()}/output/{vid}/slides.html"
    return (
        f'<div class="conflow-source" style="font-size:14px;opacity:.75;'
        f'border-left:3px solid #888;padding:6px 12px;margin-bottom:20px">'
        f'本文由 ConFlow 从视频重建：'
        f'<a href="{video_url}" target="_blank">{meta.get("title", vid)}</a>'
        f'（{meta.get("uploader", "")}）· '
        f'<a href="{slide_url}" target="_blank">配套幻灯片（可放映）</a></div>'
    )


def _slug(vid: str) -> str:
    return f"conflow-{vid.lower()}"


# -------------------------------------------------------------- openflow ----

def push_openflow(workdir: pathlib.Path, meta: dict, doc_md: str, cfg: dict) -> dict:
    return pushof.push(workdir, meta, doc_md)


# ------------------------------------------------------------- wordpress ----

def push_wordpress(workdir: pathlib.Path, meta: dict, doc_md: str, cfg: dict) -> dict:
    base = (cfg.get("wp_base") or "").strip().rstrip("/")
    user = (cfg.get("wp_user") or "").strip()
    app_pw = (cfg.get("wp_app_password") or "").strip()
    if not (base and user and app_pw):
        raise RuntimeError("WordPress 需配置站点地址(wp_base)、用户名(wp_user)与应用密码(wp_app_password)")
    vid = workdir.name
    title = (meta.get("title") or vid)[:120]
    content = _source_header(meta, vid) + _md2html(doc_md)
    body = json.dumps({
        "title": title,
        "content": content,
        "excerpt": _excerpt(content, 160),
        "status": "draft" if (cfg.get("status") or "draft") == "draft" else "publish",
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/wp-json/wp/v2/posts", data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": "Basic " + base64.b64encode(f"{user}:{app_pw}".encode()).decode()})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not data.get("id"):
        raise RuntimeError(f"WordPress 返回异常：{str(data)[:200]}")
    return {"id": f"conflow_{vid}", "slug": data.get("slug") or _slug(vid),
            "status": data.get("status", "draft"), "target": "wordpress",
            "wp_id": data["id"], "link": data.get("link"), "title": title}


# ---------------------------------------------------------------- static ----

_PAGE_TMPL = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><style>
body{{margin:0;background:oklch(96.5% .014 85);font-family:Songti SC,"Noto Serif SC",Georgia,serif}}
.page{{max-width:820px;margin:0 auto;background:#fff;padding:56px 64px;line-height:1.9;color:#1f1a14;font-size:16.5px}}
h1{{font-size:28px;line-height:1.4}} h2{{border-left:4px solid #2563eb;padding-left:12px;margin-top:32px}}
img{{max-width:100%}} code{{background:#f3f4f6;padding:1px 6px;border-radius:4px;font-size:.88em}}
pre{{background:#f6f8fa;padding:14px;border-radius:8px;overflow-x:auto}} pre code{{background:none}}
blockquote{{border-left:3px solid #9ca3af;margin:14px 0;padding:2px 16px;color:#57534e}}
a{{color:#2563eb}} .kicker{{font-family:system-ui;letter-spacing:.2em;color:#2563eb;font-size:12px;font-weight:700;margin-bottom:12px}}
</style></head><body><div class="page"><div class="kicker">CONFLOW · 视频重构</div>{body}</div></body></html>"""


def push_static(workdir: pathlib.Path, meta: dict, doc_md: str, cfg: dict) -> dict:
    out_dir = (cfg.get("static_dir") or "").strip()
    if not out_dir:
        raise RuntimeError("静态目录推送需配置 static_dir（产物 HTML 的输出目录）")
    vid = workdir.name
    out = pathlib.Path(out_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    title = (meta.get("title") or vid)[:120]
    body = _source_header(meta, vid) + _md2html(doc_md)
    path = out / f"{_slug(vid)}.html"
    path.write_text(_PAGE_TMPL.format(title=title, body=body), encoding="utf-8")
    return {"id": f"conflow_{vid}", "slug": _slug(vid), "status": "written",
            "target": "static", "path": str(path), "title": title}


# --------------------------------------------------------------- webhook ----

def push_webhook(workdir: pathlib.Path, meta: dict, doc_md: str, cfg: dict) -> dict:
    url = (cfg.get("webhook_url") or "").strip()
    if not url.startswith(("http://", "https://")):
        raise RuntimeError("Webhook 推送需配置 webhook_url（http(s)://…）")
    vid = workdir.name
    title = (meta.get("title") or vid)[:120]
    payload = {
        "id": f"conflow_{vid}", "slug": _slug(vid), "title": title,
        "source_video": meta.get("url") or "", "uploader": meta.get("uploader") or "",
        "slides_url": f"{_slide_base()}/output/{vid}/slides.html",
        "status": cfg.get("status", "draft"), "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "markdown": doc_md, "html": _source_header(meta, vid) + _md2html(doc_md),
    }
    headers = {"Content-Type": "application/json"}
    if (cfg.get("webhook_secret") or "").strip():
        headers["X-ConFlow-Secret"] = cfg["webhook_secret"].strip()
    req = urllib.request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                                 headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        code, body = resp.status, resp.read(2000).decode("utf-8", "replace")
    if code >= 300:
        raise RuntimeError(f"webhook 返回 {code}：{body[:200]}")
    return {"id": payload["id"], "slug": payload["slug"], "status": "sent",
            "target": "webhook", "response": body[:200], "title": title}


# -------------------------------------------------------------- 调度入口 ----

BUILTIN_ADAPTERS = {
    "openflow": push_openflow,
    "wordpress": push_wordpress,
    "static": push_static,
    "webhook": push_webhook,
}


def _all_adapters() -> dict:
    """内置 + 插件提供的适配器（插件目标名 = plugins/<目录名>）。"""
    return {**BUILTIN_ADAPTERS, **plugins.push_adapters()}


def push(workdir: pathlib.Path, meta: dict, doc_md: str) -> dict:
    """按 cfg["push"]["target"] 分发；结果 dict 统一带 target 字段。"""
    cfg = store.load()["push"]
    target = (cfg.get("target") or "openflow").strip().lower()
    fn = _all_adapters().get(target)
    if not fn:
        raise RuntimeError(f"未知推送目标：{target}（可选：{', '.join(_all_adapters())}）")
    result = fn(workdir, meta, doc_md, cfg)
    result.setdefault("target", target)
    return result
