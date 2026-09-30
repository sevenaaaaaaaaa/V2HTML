"""ConFlow 服务端 · LLM 配置桥（store 热读 → engine.llm provider）。

语义核心已迁至 engine/；本模块只做两件事：
  1. 把 server-data/config.json 的热配置注入 engine.llm（服务端权威来源）
  2. 兼容导出 engine 接口（app.py / admin.py 无感）
"""
from __future__ import annotations

from engine import llm as _engine

from . import store

_engine.set_provider(lambda: store.load()["llm"])

available = _engine.available
info = _engine.info
chat = _engine.chat
test_connection = _engine.test_connection
image_part = _engine.image_part
strip_fence = _engine.strip_fence
