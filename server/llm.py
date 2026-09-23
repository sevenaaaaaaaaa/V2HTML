"""V2HTML 服务端 · LLM 客户端（配置热读：server-data/config.json 优先）。"""
from __future__ import annotations

import base64
import json
import pathlib
import urllib.request

from . import store


def _llm_cfg() -> dict:
    return store.load()["llm"]


def available() -> bool:
    return bool(_llm_cfg().get("api_key"))


def info() -> dict:
    c = _llm_cfg()
    return {"llm_configured": bool(c.get("api_key")), "llm_base_url": c.get("base_url"),
            "llm_model": c.get("model"), "vision": bool(c.get("vision"))}


def chat(messages: list[dict], temperature: float = 0.4, max_tokens: int | None = None) -> str:
    c = _llm_cfg()
    if not c.get("api_key"):
        raise RuntimeError("LLM 未配置：请在管理后台「系统配置」填写 API Key")
    body = json.dumps({"model": c.get("model"), "messages": messages,
                       "temperature": temperature,
                       "max_tokens": max_tokens or int(c.get("max_tokens") or 8192)}).encode()
    req = urllib.request.Request(
        c.get("base_url").rstrip("/") + "/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {c['api_key']}"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]


def test_connection() -> tuple[bool, str]:
    try:
        out = chat([{"role": "user", "content": "回复两个字：正常"}],
                   temperature=0, max_tokens=16)
        return True, out.strip()[:40]
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)[:200]


def image_part(path: pathlib.Path) -> dict:
    b64 = base64.b64encode(path.read_bytes()).decode()
    return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}


def strip_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()
