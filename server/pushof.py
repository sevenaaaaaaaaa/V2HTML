"""V2HTML 服务端 · 把生成的文章推送进 openflow（data/articles/index.json）。

- doc.md → HTML（markdown 库转换），头部附来源视频与幻灯片链接
- 幂等：同 video_id 再次推送为覆盖更新
- 写入前备份 index.json（保留最近 5 份），写入后恢复原文件属主
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import time

import markdown as md_lib

from . import store

SLIDE_BASE = os.environ.get("V2HTML_PUBLIC_BASE", "/VTH")  # 本站 slides 的对外前缀


def _md2html(doc_md: str) -> str:
    return md_lib.markdown(doc_md, extensions=["extra", "toc"])


def _excerpt(html: str, limit: int = 120) -> str:
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def push(workdir: pathlib.Path, meta: dict, doc_md: str) -> dict:
    cfg = store.load()["push"]
    data_root = pathlib.Path(cfg["openflow_data"])
    index_path = data_root / "articles" / "index.json"
    if not index_path.exists():
        raise RuntimeError(f"openflow 文章索引不存在：{index_path}")

    vid = workdir.name
    html = _md2html(doc_md)
    slide_url = f"{SLIDE_BASE}/output/{vid}/slides.html"
    video_url = meta.get("url") or ""
    header = (
        f'<div class="v2html-source" style="font-size:14px;opacity:.75;'
        f'border-left:3px solid #888;padding:6px 12px;margin-bottom:20px">'
        f'本文由 V2HTML 从视频重建：'
        f'<a href="{video_url}" target="_blank">{meta.get("title", vid)}</a>'
        f'（{meta.get("uploader", "")}）· '
        f'<a href="{slide_url}" target="_blank">配套幻灯片（可放映）</a></div>'
    )
    content = header + html

    # 分类校验
    cat = cfg.get("category") or "ai-create"
    cats_file = data_root / "article-categories.json"
    try:
        valid = list(json.loads(cats_file.read_text(encoding="utf-8")).keys())
        if cat not in valid and valid:
            cat = "ai-create" if "ai-create" in valid else valid[0]
    except Exception:
        pass

    now = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        "id": f"v2html_{vid}",
        "title": (meta.get("title") or vid)[:120],
        "slug": f"v2html-{vid.lower()}",
        "content": content,
        "excerpt": _excerpt(content),
        "status": cfg.get("status", "draft"),
        "author": cfg.get("author", "V2HTML 引擎"),
        "category": cat,
        "tags": ["V2HTML", "视频重构", meta.get("uploader") or "视频"],
        "source": "v2html",
        "created_at": now,
        "updated_at": now,
        "seo_title": (meta.get("title") or vid)[:120],
        "seo_desc": _excerpt(content, 160),
        "cover": "",
    }

    stat_before = index_path.stat()
    # 备份（保留最近 5 份）
    bak = index_path.with_name(f"index.json.bak-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(index_path, bak)
    p = pathlib.Path(data_root / "articles")
    baks = sorted(p.glob("index.json.bak-*"))
    for old in baks[:-5]:
        old.unlink(missing_ok=True)

    articles = json.loads(index_path.read_text(encoding="utf-8"))
    articles = [a for a in articles if a.get("id") != entry["id"]]
    articles.insert(0, entry)
    tmp = index_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(articles, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, index_path)
    try:  # 恢复属主（openflow PHP 以 www 运行）
        os.chown(index_path, stat_before.st_uid, stat_before.st_gid)
        os.chmod(index_path, stat_before.st_mode)
    except Exception:
        pass
    return {"id": entry["id"], "slug": entry["slug"], "status": entry["status"],
            "category": entry["category"], "title": entry["title"],
            "admin_url": "/xmp/content-hub?tab=articles"}
