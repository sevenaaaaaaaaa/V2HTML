"""示例推送适配器：把推送回执写到本地 receipt.txt。

插件规范 v1：目录名即推送目标名（这里是 example-receipt），
实现 push(workdir, meta, doc_md, cfg) -> dict 即完成注册。
"""
from __future__ import annotations

import pathlib
import time


def push(workdir: pathlib.Path, meta: dict, doc_md: str, cfg: dict) -> dict:
    out_dir = pathlib.Path(cfg.get("static_dir") or "output").expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    receipt = out_dir / f"receipt-{workdir.name}.txt"
    receipt.write_text(
        f"ConFlow 推送回执\n"
        f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"视频: {meta.get('title')} ({meta.get('url')})\n"
        f"文档: {len(doc_md)} 字符\n",
        encoding="utf-8")
    return {"id": f"conflow_{workdir.name}", "slug": f"conflow-{workdir.name.lower()}",
            "status": "written", "path": str(receipt), "title": meta.get("title")}
