"""V2HTML 服务端 · 配置与凭据存储。

优先级：server-data/config.json > 环境变量 > 内置默认。
server-data/ 不进代码库（含密钥哈希与 LLM key）。
"""
from __future__ import annotations

import copy
import json
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "server-data"
CFG_PATH = DATA_DIR / "config.json"

DEFAULTS: dict = {
    "llm": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key": "",
        "model": "glm-4.7",
        "max_tokens": 8192,
        "vision": False,
    },
    "push": {
        "enabled": True,          # 任务完成后自动推送到 openflow
        "status": "draft",        # draft（进 openflow 后台待发）| published（直接上线）
        "category": "ai-create",
        "author": "V2HTML 引擎",
        "openflow_data": "/www/wwwroot/nownexts_com/data",
    },
    "admin": {},                  # {"username":…, "salt":…, "hash":…}
}

_lock = None


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load() -> dict:
    cfg = copy.deepcopy(DEFAULTS)
    if CFG_PATH.exists():
        try:
            cfg = _deep_merge(cfg, json.loads(CFG_PATH.read_text(encoding="utf-8")))
        except Exception:
            pass
    # 环境变量兜底（首次部署未写 config 时仍能用 .env 跑起来）
    env_map = {
        ("llm", "base_url"): "V2HTML_LLM_BASE_URL",
        ("llm", "api_key"): "V2HTML_LLM_API_KEY",
        ("llm", "model"): "V2HTML_LLM_MODEL",
        ("llm", "max_tokens"): "V2HTML_LLM_MAX_TOKENS",
        ("push", "openflow_data"): "V2HTML_OPENFLOW_DATA",
    }
    for (sec, key), var in env_map.items():
        if not cfg[sec].get(key) and os.environ.get(var):
            cfg[sec][key] = os.environ[var]
    if cfg["llm"].get("max_tokens") in (None, "", "None"):
        cfg["llm"]["max_tokens"] = 8192
    return cfg


def save(cfg: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CFG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, CFG_PATH)
    os.chmod(CFG_PATH, 0o600)


def update(section: str, patch: dict) -> dict:
    cfg = load()
    cfg.setdefault(section, {}).update(patch)
    save(cfg)
    return cfg
