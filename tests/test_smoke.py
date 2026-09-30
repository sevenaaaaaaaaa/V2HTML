#!/usr/bin/env python3
"""ConFlow 冒烟与 mock E2E 测试（离线：mock LLM 端点，不触网、不需要 key）。

运行: python3 tests/test_smoke.py        （依赖：requirements.txt + httpx2）
CI:   .github/workflows/ci.yml 的 smoke job 调用本文件。
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("CONFLOW_LLM_API_KEY", "sk-test")
os.environ.setdefault("CONFLOW_LLM_BASE_URL", "http://127.0.0.1:18990/v1")
os.environ.setdefault("CONFLOW_LLM_MODEL", "mock")

PASS = []


def ok(name: str) -> None:
    PASS.append(name)
    print(f"  ✓ {name}")


# ---------------------------------------------------------------- mock LLM ----

EN_DOC = ("# Rust in 100 Seconds: What the Type System Buys\n\n"
          "## Hook\n\nBlazing speed, 3 a.m. segfaults [00:10].\n\n"
          "## Limits\n\nSteep curve. ⚠️ completion: async not covered.")
EN_SECTIONS = ('<section class="slide cover active"><div class="kicker">T</div>'
               '<h1>Rust</h1><p class="sub">s</p></section>'
               '<section class="slide"><div class="kicker">S</div><h2>Ownership</h2>'
               '<div class="hrule"></div><div class="body"><ul class="bullets">'
               '<li>One owner per value</li></ul></div></section>')
SCRIPT_MD = ("# 钩子式标题\n\n> 预计时长 52s · 适用平台：抖音 / Shorts / Reels\n\n"
             "## 节拍表\n\n| # | 秒 | 口播词 | 画面提示 | 屏幕大字 |\n|---|---|---|---|---|\n"
             "| 1 | 3 | 钩子 | 特写 | ownership |\n\n"
             "## 衔接 v2video\n\n- style：极简扁平信息图风\n- 转换说明：每拍 → storyboard.json 的一个 shot。")
STORYBOARD = {"title": "分镜", "duration_sec": 60, "aspect": "16:9", "style": "极简信息图",
              "shots": [{"id": 1, "sec": 4, "scene": "齿轮特写", "motion": "推近",
                         "narration": "为什么 Rust？", "on_screen": "ownership",
                         "transition": "cut",
                         "prompts": {"sora": "gear", "veo": "gear macro", "kling": "齿轮特写"}}]}


class MockLLM(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        sys_p = body["messages"][0]["content"]
        user_p = body["messages"][-1]["content"]
        captured["sys"] = sys_p
        captured["user"] = user_p
        if body.get("max_tokens") == 8:
            out = "science"
        elif "短视频口播脚本" in sys_p:
            out = SCRIPT_MD
        elif "storyboard.json 本体" in sys_p:
            out = json.dumps(STORYBOARD, ensure_ascii=False)
        elif "幻灯片" in sys_p:
            out = EN_SECTIONS if "English" in sys_p else \
                '<section class="slide cover active"><h1>中文封面</h1></section>'
        else:
            out = EN_DOC if "English" in sys_p else "# 中文文档\n\n## 一节\n\n内容。"
        data = json.dumps({"choices": [{"message": {"content": out}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


captured: dict = {}
srv = HTTPServer(("127.0.0.1", 18990), MockLLM)
threading.Thread(target=srv.serve_forever, daemon=True).start()


# ------------------------------------------------------------- 1. 引擎 ----

print("[engine]")
from engine import batch, generate, llm, plugins, qc, storyboard  # noqa: E402

meta = {"title": "T", "uploader": "U", "duration_sec": 100, "url": "https://x"}
tr = "[00:10] hello world " * 50

doc_en = generate.gen_doc("science", meta, tr, None, language="en")
assert "English" in captured["sys"] and "防幻觉规则不因语言改变" in captured["sys"]
assert doc_en.startswith("# Rust in 100 Seconds")
ok("gen_doc(en) 语言指令注入")

deck_en = generate.build_deck(EN_SECTIONS, "T", "science", language="en")
assert '<html lang="en" data-theme="science">' in deck_en
deck_zh = generate.build_deck('<section class="slide cover active"><h1>x</h1></section>', "t", "science")
assert '<html lang="zh-CN" data-theme="science">' in deck_zh
ok("build_deck html lang 同步（en / 默认 zh-CN）")

script = generate.gen_short_script("science", doc_en, meta, language="zh")
assert "短视频口播脚本" in captured["sys"] and "节拍表" in script and "storyboard.json" in script
ok("gen_short_script 节拍表 + v2video 衔接")

sb = storyboard.gen_storyboard(doc_en, meta, language="en", duration=60)
assert "storyboard.json 本体" in captured["sys"] and "60 秒" in captured["sys"]
tmp = pathlib.Path(tempfile.mkdtemp())
out = storyboard.write_storyboard(tmp, sb)
assert (out / "storyboard.json").exists() and (out / "narration.md").exists()
assert "00:00:00,000 --> 00:00:04,000" in (out / "subs.srt").read_text(encoding="utf-8")
assert (out / "README.md").exists()
ok("storyboard 四件套 + srt 时间轴")

# ------------------------------------------------------------- 2. 插件 ----

print("[plugins]")
d = plugins.discover(force=True)
assert "example-receipt" in d["push"] and d["themes_css"] is not None
ok("示例插件发现（推送适配器注册）")

from server import pushers  # noqa: E402

ad = pushers._all_adapters()
assert {"openflow", "wordpress", "static", "webhook", "example-receipt"} <= set(ad)
tmp2 = pathlib.Path(tempfile.mkdtemp())
r = ad["example-receipt"](pathlib.Path(tmp), {"title": "T", "url": "u"}, "# doc",
                          {"static_dir": str(tmp2)})
assert pathlib.Path(r["path"]).exists()
ok("推送目标合并（内置 4 + 插件）与插件调用")

# ------------------------------------------------------------- 3. 服务端 ----

print("[server]")
os.environ["CONFLOW_TOKEN"] = "testtoken123"
from fastapi.testclient import TestClient  # noqa: E402

from server import app as appmod  # noqa: E402
from server import jobsdb  # noqa: E402

appmod.EXEC.submit = lambda fn, *a: None      # 离线：入队但不执行
c = TestClient(appmod.app)
H = {"Authorization": "Bearer testtoken123"}

h = c.get("/api/health").json()
assert h["themes"] == 30 and "push_enabled" in h
ok("health")

r = c.post("/api/jobs", json={"url": "https://x.ly/v", "language": "xx"},
           headers=H)
assert r.status_code == 400
r = c.post("/api/jobs", json={"url": "https://x.ly/v", "script": True,
                              "storyboard": True, "language": "en"}, headers=H)
jid = r.json()["id"]
job = appmod.JOBS[jid]
assert job["script"] and job["storyboard"] and job["language"] == "en"
job["video_id"] = "vidX"                      # 模拟素材就绪后的 artifacts 映射
d = c.get(f"/api/jobs/{jid}", headers=H).json()
assert d["artifacts"]["script"] == "output/vidX/script.md"
assert d["artifacts"]["storyboard"] == "output/vidX/storyboard/storyboard.json"
ok("任务参数（script/storyboard/language）入队与 artifacts")

r = c.post("/api/subs", json={"url": "https://x.ly/@ch", "name": "测试",
                              "language": "en", "script": True, "storyboard": True},
           headers=H)
sid = r.json()["id"]
sub = jobsdb.sub_get(sid)
assert sub["language"] == "en" and sub["script"] == 1 and sub["storyboard"] == 1
ok("订阅源级 language/script/storyboard 持久化")

fake = [{"id": "vidDone1", "title": "已做过", "url": "https://x.ly/watch?v=vidDone1"},
        {"id": "vidNew1", "title": "新视频", "url": "https://x.ly/watch?v=vidNew1"}]
saved_out = appmod.OUT
tmpout = pathlib.Path(tempfile.mkdtemp())
(tmpout / "vidDone1").mkdir()
(tmpout / "vidDone1" / "doc.md").write_text("x", encoding="utf-8")
appmod.OUT = tmpout
appmod.batch.expand = lambda url, limit=20, proxy=None: fake
r = c.post("/api/jobs", json={"url": "https://x.ly/@ch"}, headers=H)
assert len(r.json()["batch"]) == 1 and r.json()["skipped"] == 1
r = c.post(f"/api/subs/{sid}/check", headers=H).json()
assert r["total"] == 2 and r["skipped"] >= 1
ok("批量展开 + 产物去重 + 订阅 check")

for jid2 in [j for j in appmod.JOBS if appmod.JOBS[j]["url"].startswith("https://x.ly")]:
    appmod.JOBS.pop(jid2, None)
    jobsdb.delete(jid2)
c.post(f"/api/subs/{sid}/delete", headers=H)
jobsdb.sub_delete(sid)
appmod.OUT = saved_out
appmod.batch.expand = batch.expand

assert c.get("/api/subs").status_code == 401
ok("无 token 401")

srv.shutdown()
print(f"\nALL {len(PASS)} SMOKE TESTS PASS")
