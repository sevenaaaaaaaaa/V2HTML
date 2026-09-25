"""V2HTML 服务端 · 管理后台（设计语言对齐 OpenFlow：oklch tokens + 玻璃卡片 + 侧栏）。

子路径部署适配：所有跳转、表单 action、链接、fetch 均基于 request.scope["root_path"]
（服务端以 `uvicorn --root-path /VTH` 启动；本地裸跑时 root_path 为空，两态通用）。
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from . import auth, llm, store

router = APIRouter()

TOKENS = """
:root{
  --bg:oklch(96.5% .016 85);--bg-soft:oklch(94% .02 85);--surface:oklch(100% 0 0/.62);
  --surface-strong:oklch(100% 0 0/.88);--fg:oklch(22% .02 70);--muted:oklch(46% .016 70);
  --faint:oklch(51% .014 75);--border:oklch(86% .014 80);--border-strong:oklch(76% .02 80);
  --hover:oklch(22% .02 70/.055);--accent:oklch(52% .17 258);--accent-strong:oklch(46% .17 258);
  --accent-soft:oklch(52% .17 258/.12);--on-accent:oklch(100% 0 0);
  --ok:oklch(58% .17 152);--ok-soft:oklch(58% .17 152/.12);
  --warn:oklch(66% .15 75);--warn-soft:oklch(66% .15 75/.14);
  --danger:oklch(55% .2 25);--danger-soft:oklch(55% .2 25/.12);
  --glass:oklch(100% 0 0/.5);--glass-border:oklch(100% 0 0/.68);
  --shadow:0 24px 60px -24px oklch(30% .04 80/.28);--shadow-sm:0 10px 28px -14px oklch(30% .04 80/.22);
  --r-lg:26px;--r-md:18px;--r-sm:12px;--sb-w:232px;
  --font:"Space Grotesk","PingFang SC","HarmonyOS Sans SC","MiSans","Segoe UI",system-ui,sans-serif;
  --mono:ui-monospace,"SF Mono","JetBrains Mono",Menlo,monospace;
  --ease-spring:cubic-bezier(.32,.72,0,1);
}
@media (prefers-color-scheme:dark){:root{
  --bg:oklch(19% .014 70);--bg-soft:oklch(22.5% .014 72);--surface:oklch(26% .016 72/.6);
  --surface-strong:oklch(28% .016 72/.9);--fg:oklch(93% .012 80);--muted:oklch(72% .014 75);
  --faint:oklch(64% .014 75);--border:oklch(38% .014 75);--border-strong:oklch(48% .016 75);
  --hover:oklch(93% .012 80/.06);--accent-soft:oklch(52% .17 258/.22);
  --ok-soft:oklch(58% .17 152/.2);--warn-soft:oklch(66% .15 75/.2);--danger-soft:oklch(55% .2 25/.2);
  --glass:oklch(28% .016 72/.5);--glass-border:oklch(40% .016 75/.5);
  --shadow:0 24px 60px -24px oklch(0% 0 0/.5);--shadow-sm:0 10px 28px -14px oklch(0% 0 0/.45)}}
"""

CSS = TOKENS + """
*{box-sizing:border-box;margin:0}
body{background:var(--bg);color:var(--fg);font-family:var(--font);min-height:100vh;
  background-image:radial-gradient(760px 420px at 88% -8%,var(--accent-soft),transparent 60%),
  radial-gradient(600px 380px at -6% 104%,var(--accent-soft),transparent 55%)}
a{color:var(--accent);text-decoration:none;word-break:break-all}
.layout{display:flex;min-height:100vh}
.sb{width:var(--sb-w);flex:none;padding:22px 14px;display:flex;flex-direction:column;gap:4px;
  position:sticky;top:0;height:100vh}
.sb .logo{font-size:20px;font-weight:750;letter-spacing:.02em;padding:6px 12px 18px}
.sb .logo small{display:block;font-size:11px;color:var(--muted);letter-spacing:.18em;font-weight:500}
.sb a.nav{display:flex;align-items:center;gap:10px;padding:10px 14px;border-radius:12px;
  color:var(--fg);font-size:14.5px;font-weight:550;transition:background .25s var(--ease-spring)}
.sb a.nav:hover{background:var(--hover)}
.sb a.nav.on{background:var(--accent-soft);color:var(--accent-strong);font-weight:700}
.sb .sp{flex:1}
.sb .who{font-size:12.5px;color:var(--muted);padding:10px 14px}
.main{flex:1;padding:30px 36px 60px;max-width:1080px;min-width:0}
h1{font-size:26px;margin-bottom:6px}
.sub{color:var(--muted);font-size:14px;margin-bottom:26px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:16px;margin-bottom:26px}
.card{background:var(--glass);border:1px solid var(--glass-border);border-radius:var(--r-md);
  padding:18px 20px;backdrop-filter:blur(14px);box-shadow:var(--shadow-sm)}
.card .k{font-size:12.5px;color:var(--muted);letter-spacing:.06em}
.card .v{font-size:26px;font-weight:750;margin-top:6px}
.card .v small{font-size:13px;font-weight:500;color:var(--muted)}
.panel{background:var(--glass);border:1px solid var(--glass-border);border-radius:var(--r-lg);
  padding:24px 26px;backdrop-filter:blur(14px);box-shadow:var(--shadow);margin-bottom:22px}
.panel h2{font-size:16.5px;margin-bottom:16px}
table{width:100%;border-collapse:collapse;font-size:14px}
th{text-align:left;font-size:12px;color:var(--muted);letter-spacing:.08em;padding:8px 10px;
  border-bottom:2px solid var(--border)}
td{padding:11px 10px;border-bottom:1px solid var(--border);vertical-align:top}
tr:last-child td{border-bottom:none}
.btn{display:inline-block;background:var(--accent);color:var(--on-accent);border:none;border-radius:10px;
  padding:9px 18px;font-size:14px;font-weight:650;cursor:pointer;font-family:var(--font)}
.btn.sm{padding:5px 12px;font-size:12.5px;border-radius:8px}
.btn.ghost{background:transparent;color:var(--accent);border:1.5px solid var(--accent)}
.btn.danger{background:var(--danger-soft);color:var(--danger)}
.btn:disabled{opacity:.5}
input,select{background:var(--surface-strong);border:1px solid var(--border);border-radius:10px;
  color:var(--fg);padding:9px 12px;font-size:14px;width:100%;font-family:var(--font)}
label{display:block;font-size:12.5px;color:var(--muted);margin:12px 0 5px;letter-spacing:.05em}
.badge{display:inline-block;padding:2px 10px;border-radius:20px;font-size:12px;font-weight:700}
.b-queued{background:var(--hover)}.b-running{background:var(--accent-soft);color:var(--accent-strong)}
.b-done{background:var(--ok-soft);color:var(--ok)}.b-error{background:var(--danger-soft);color:var(--danger)}
.b-paused_no_llm{background:var(--warn-soft);color:var(--warn)}
.steps{font-family:var(--mono);font-size:12.5px;color:var(--muted);line-height:1.9}
.login-wrap{min-height:100vh;display:grid;place-items:center;padding:24px}
.login{background:var(--glass);border:1px solid var(--glass-border);border-radius:var(--r-lg);
  padding:38px 42px;backdrop-filter:blur(16px);box-shadow:var(--shadow);width:400px}
.err{background:var(--danger-soft);color:var(--danger);border-radius:10px;padding:9px 14px;
  font-size:13.5px;margin-bottom:14px}
.ok{background:var(--ok-soft);color:var(--ok);border-radius:10px;padding:9px 14px;font-size:13.5px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:0 22px}
iframe{width:100%;height:560px;border:1px solid var(--border);border-radius:var(--r-sm);background:#fff}
.inline-form{display:inline}
"""


def rp_of(request: Request) -> str:
    """子路径前缀（--root-path /VTH 时为 /VTH；本地裸跑为空）。"""
    return (request.scope.get("root_path") or "").rstrip("/")


def page(rp: str, title: str, active: str, body: str, user: str | None = None) -> HTMLResponse:
    navs = [("dashboard", "仪表盘", rp + "/admin"), ("jobs", "任务管理", rp + "/admin/jobs"),
            ("config", "系统配置", rp + "/admin/config")]
    nav = "".join(
        f'<a class="nav{" on" if key == active else ""}" href="{href}">{label}</a>'
        for key, label, href in navs)
    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · V2HTML 后台</title><style>{CSS}</style></head><body>
<div class="layout"><aside class="sb">
  <div class="logo">V2HTML<small>视频 ⇄ 内容引擎 · 管理</small></div>
  {nav}<div class="sp"></div>
  <div class="who">👤 {user or ""}</div>
  <a class="nav" href="{rp}/admin/logout">退出登录</a>
  <a class="nav" href="{rp}/" target="_blank">打开前台 ↗</a>
</aside><main class="main">{body}</main></div></body></html>"""
    return HTMLResponse(html)


def _user(request: Request) -> str | None:
    return auth.check_session(request.cookies.get("v2h_session"))


def _guard(request: Request):
    if not _user(request):
        return RedirectResponse(rp_of(request) + "/admin/login", 302)
    return None


# ------------------------------------------------------------------ login ----

@router.get("/admin/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = ""):
    if _user(request):                       # 已登录直接进仪表盘
        return RedirectResponse(rp_of(request) + "/admin/", 302)
    rp = rp_of(request)
    body = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>登录 · V2HTML 后台</title><style>{CSS}
body{{display:grid;place-items:center;min-height:100vh;padding:24px}}
</style></head><body><div class="login-wrap"><div class="login">
    <h1>V2HTML 管理后台</h1>
    <p class="sub" style="margin-bottom:20px">视频 ⇄ HTML 双向内容引擎</p>
    {'<div class="err">' + error + "</div>" if error else ""}
    <form method="post" action="{rp}/admin/login">
      <label>账号</label><input name="username" autocomplete="username" required autofocus>
      <label>密码</label><input name="password" type="password" autocomplete="current-password" required>
      <div style="margin-top:20px"><button class="btn" style="width:100%">登录</button></div>
    </form>
    <p class="sub" style="margin:18px 0 0"><a href="{rp}/">← 返回前台</a></p>
  </div></div></body></html>"""
    return HTMLResponse(body)


@router.post("/admin/login")
async def login_do(request: Request):
    rp = rp_of(request)
    form = await request.form()
    u, p = str(form.get("username", "")), str(form.get("password", ""))
    if auth.verify_credentials(u, p):
        resp = RedirectResponse(rp + "/admin/", 302)
        resp.set_cookie("v2h_session", auth.make_session(u), httponly=True,
                        samesite="lax", max_age=7 * 86400)
        return resp
    return RedirectResponse(rp + "/admin/login?error=账号或密码错误", 302)


@router.get("/admin/logout")
def logout(request: Request):
    resp = RedirectResponse(rp_of(request) + "/admin/login", 302)
    resp.delete_cookie("v2h_session")
    return resp


# ------------------------------------------------------------- dashboard ----

@router.get("/admin/", response_class=HTMLResponse)
def dashboard(request: Request):
    g = _guard(request)
    if g:
        return g
    user = _user(request)
    rp = rp_of(request)
    from .app import JOBS
    jobs = list(JOBS.values())
    done = sum(1 for j in jobs if j["status"] == "done")
    err = sum(1 for j in jobs if j["status"] == "error")
    run = sum(1 for j in jobs if j["status"] in ("queued", "running"))
    info = llm.info()
    cfg = store.load()
    recent = sorted(jobs, key=lambda j: j["t0"], reverse=True)[:6]
    rows = "".join(
        f"<tr><td><span class='badge b-{j['status']}'>{j['status']}</span></td>"
        f"<td><a href='{rp}/admin/jobs/{j['id']}'>{(j.get('title') or j['url'])[:44]}</a></td>"
        f"<td>{j['doc_type']}</td><td>{j['theme']}</td></tr>"
        for j in recent) or "<tr><td colspan=4 style='color:var(--muted)'>还没有任务</td></tr>"
    body = f"""
    <h1>仪表盘</h1><p class="sub">V2HTML 服务运行概览</p>
    <div class="cards">
      <div class="card"><div class="k">任务总数</div><div class="v" id="st-total">{len(jobs)}</div></div>
      <div class="card"><div class="k">进行中</div><div class="v" id="st-run">{run}</div></div>
      <div class="card"><div class="k">已完成</div><div class="v" id="st-done">{done}</div></div>
      <div class="card"><div class="k">失败</div><div class="v" id="st-err">{err}</div></div>
    </div>
    <div class="cards">
      <div class="card"><div class="k">LLM</div>
        <div class="v" style="font-size:17px">{'✅ ' + info['llm_model'] if info['llm_configured'] else '⚠️ 未配置'}</div></div>
      <div class="card"><div class="k">自动推送 openflow</div>
        <div class="v" style="font-size:17px">{'✅ 开启 · ' + cfg['push']['status'] if cfg['push']['enabled'] else '已关闭'}</div></div>
      <div class="card"><div class="k">幻灯片主题库</div><div class="v">30 <small>个</small></div></div>
      <div class="card"><div class="k">前台入口</div>
        <div class="v" style="font-size:15px"><a href="{rp}/" target="_blank">{rp or '/'} ↗</a></div></div>
    </div>
    <div class="panel"><h2>最近任务</h2><table>
      <tr><th>状态</th><th>标题 / 链接</th><th>文体</th><th>主题</th></tr>{rows}</table></div>
    <div class="panel"><h2>快速提交</h2>
      <form method="post" action="{rp}/admin/jobs/create">
        <div class="grid2">
          <div style="grid-column:1/-1"><label>视频链接</label>
            <input name="url" placeholder="https://www.youtube.com/watch?v=xxxx" required></div>
          <div><label>文体</label><select name="doc_type">
            <option value="auto">自动判定</option><option value="tutorial">教程</option>
            <option value="science">科普</option><option value="commentary">评论</option>
            <option value="other">其他</option></select></div>
          <div><label>主题（auto=跟随文体）</label><input name="theme" value="auto"></div>
        </div>
        <div style="margin-top:18px"><button class="btn">生成文档 + 幻灯片</button></div>
      </form></div>
    <script>
    async function poll(){{
      try{{
        const jobs = await (await fetch("{rp}/api/jobs")).json();
        document.getElementById("st-total").textContent = jobs.length;
        document.getElementById("st-run").textContent = jobs.filter(j=>["queued","running"].includes(j.status)).length;
        document.getElementById("st-done").textContent = jobs.filter(j=>j.status==="done").length;
        document.getElementById("st-err").textContent = jobs.filter(j=>j.status==="error").length;
      }}catch(e){{}}
    }}
    setInterval(poll, 5000);
    </script>"""
    return page(rp, "仪表盘", "dashboard", body, user)


# ------------------------------------------------------------------- jobs ----

@router.get("/admin/jobs/", response_class=HTMLResponse)
def jobs_page(request: Request):
    g = _guard(request)
    if g:
        return g
    user = _user(request)
    rp = rp_of(request)
    from .app import JOBS
    rows = ""
    for j in sorted(JOBS.values(), key=lambda x: x["t0"], reverse=True):
        acts = f"<a class='btn sm ghost' href='{rp}/admin/jobs/{j['id']}'>详情</a> "
        if j["status"] == "done":
            acts += (f"<a class='btn sm ghost' href='{rp}/output/{j['video_id']}/slides.html' target='_blank'>幻灯片</a> "
                     f"<form class='inline-form' method='post' action='{rp}/admin/jobs/{j['id']}/push'>"
                     f"<button class='btn sm'>推送</button></form> ")
        acts += (f"<form class='inline-form' method='post' action='{rp}/admin/jobs/{j['id']}/retry'>"
                 f"<button class='btn sm ghost'>↻</button></form>"
                 f"<form class='inline-form' method='post' action='{rp}/admin/jobs/{j['id']}/delete' "
                 f"onsubmit=\"return confirm('删除任务与全部产物？')\">"
                 f"<button class='btn sm danger'>删</button></form>")
        rows += (f"<tr><td><span class='badge b-{j['status']}'>{j['status']}</span></td>"
                 f"<td><a href='{rp}/admin/jobs/{j['id']}'>{(j.get('title') or j['url'])[:40]}</a><br>"
                 f"<span style='font-size:12px;color:var(--muted)'>{j['created']}</span></td>"
                 f"<td>{j['doc_type']}<br><span style='font-size:12px;color:var(--muted)'>{j['theme']}</span></td>"
                 f"<td style='white-space:nowrap'>{acts}</td></tr>")
    body = f"""<h1>任务管理</h1><p class="sub">全部生成任务与产物入口（推送=写入 openflow 文章库）</p>
    <div class="panel"><table>
      <tr><th>状态</th><th>任务</th><th>文体·主题</th><th>操作</th></tr>
      {rows or "<tr><td colspan=4 style='color:var(--muted)'>暂无任务 — 到仪表盘底部提交第一条</td></tr>"}</table></div>"""
    return page(rp, "任务管理", "jobs", body, user)


@router.get("/admin/jobs/{jid}", response_class=HTMLResponse)
def job_detail(request: Request, jid: str):
    g = _guard(request)
    if g:
        return g
    user = _user(request)
    rp = rp_of(request)
    from .app import JOBS
    job = JOBS.get(jid)
    if not job:
        body = f"""<h1>任务不存在</h1>
          <p class="sub">任务列表保存在内存中，服务重启后会清空（产物文件仍在 {rp}/output/ 下）。</p>
          <p><a class="btn" href="{rp}/admin/jobs">返回任务列表</a></p>"""
        return page(rp, "任务不存在", "jobs", body, user)
    steps = "".join(f"<div>+{s['t']}s　{s['msg']}</div>" for s in job["steps"])
    art = ""
    if job["status"] == "done" and job["video_id"]:
        v = job["video_id"]
        pushed = ""
        if job.get("pushed"):
            pushed = (f"<div class='ok' style='margin-top:12px'>已推送 openflow："
                      f"<b>{job['pushed']['status']}</b> · {job['pushed']['slug']} — "
                      f"到 openflow 后台 content-hub 可发布</div>")
        art = f"""<div class="panel"><h2>产物</h2>
          <p style="font-size:14px;line-height:2.3">
            <a class="btn sm" href="{rp}/output/{v}/slides.html" target="_blank">▶ 放映幻灯片</a>
            <a class="btn sm ghost" href="{rp}/api/jobs/{jid}/doc" target="_blank">文档 doc.md</a>
            <a class="btn sm ghost" href="{rp}/output/{v}/transcript.md" target="_blank">转写稿</a>
            <a class="btn sm ghost" href="{rp}/output/{v}/sheet.jpg" target="_blank">关键帧联览图</a></p>
          {pushed}
          <iframe src="{rp}/api/jobs/{jid}/doc"></iframe></div>"""
    refresh = ('<meta http-equiv="refresh" content="5">'
               if job["status"] in ("queued", "running") else "")
    body = f"""<h1>任务 {jid}</h1>
    <p class="sub"><a href="{job['url']}" target="_blank">{job['url']}</a></p>
    <div class="cards">
      <div class="card"><div class="k">状态</div>
        <div class="v" style="font-size:17px"><span class="badge b-{job['status']}">{job['status']}</span>
        {'<small style="color:var(--muted)">（每 5 秒自动刷新）</small>' if refresh else ''}</div></div>
      <div class="card"><div class="k">文体 / 主题</div>
        <div class="v" style="font-size:17px">{job['doc_type']} · {job['theme']}</div></div>
      <div class="card"><div class="k">产物目录</div>
        <div class="v" style="font-size:15px">{job['video_id'] or '—'}</div></div>
    </div>
    {f'<div class="err">{job["error"]}</div>' if job['error'] else ''}
    <div class="panel"><h2>执行日志</h2><div class="steps">{steps or '—'}</div>
      <div style="margin-top:16px;display:flex;gap:10px">
        <form class="inline-form" method="post" action="{rp}/admin/jobs/{jid}/retry">
          <button class="btn sm ghost">↻ 重试</button></form>
        <form class="inline-form" method="post" action="{rp}/admin/jobs/{jid}/push">
          <button class="btn sm" {'disabled' if job['status'] != 'done' else ''}>推送 openflow</button></form>
        <form class="inline-form" method="post" action="{rp}/admin/jobs/{jid}/delete"
          onsubmit="return confirm('删除任务与全部产物？')">
          <button class="btn sm danger">删除</button></form>
      </div></div>
    {art}"""
    resp = page(rp, f"任务 {jid}", "jobs", body, user)
    if refresh:
        resp.headers["Cache-Control"] = "no-store"
    return resp


@router.post("/admin/jobs/create")
async def admin_create_job(request: Request):
    rp = rp_of(request)
    if not _user(request):
        return RedirectResponse(rp + "/admin/login", 302)
    from .app import create_job
    form = await request.form()
    jid = None
    try:
        r = await create_job({"url": str(form.get("url", "")),
                              "doc_type": str(form.get("doc_type", "auto")),
                              "theme": str(form.get("theme", "auto"))}, request)
        jid = r.get("id")
    except Exception:
        pass
    if jid:
        return RedirectResponse(rp + f"/admin/jobs/{jid}", 302)
    return RedirectResponse(rp + "/admin/jobs/", 302)


@router.post("/admin/jobs/{jid}/retry")
async def admin_retry(request: Request, jid: str):
    rp = rp_of(request)
    if not _user(request):
        return RedirectResponse(rp + "/admin/login", 302)
    from .app import retry_job
    retry_job(jid)
    return RedirectResponse(rp + f"/admin/jobs/{jid}", 302)


@router.post("/admin/jobs/{jid}/push")
async def admin_push(request: Request, jid: str):
    rp = rp_of(request)
    if not _user(request):
        return RedirectResponse(rp + "/admin/login", 302)
    from .app import push_job
    push_job(jid)
    return RedirectResponse(rp + f"/admin/jobs/{jid}", 302)


@router.post("/admin/jobs/{jid}/delete")
async def admin_delete(request: Request, jid: str):
    rp = rp_of(request)
    if not _user(request):
        return RedirectResponse(rp + "/admin/login", 302)
    from .app import delete_job
    delete_job(jid)
    return RedirectResponse(rp + "/admin/jobs/", 302)


# ----------------------------------------------------------------- config ----

@router.get("/admin/config/", response_class=HTMLResponse)
def config_page(request: Request, saved: str = ""):
    g = _guard(request)
    if g:
        return g
    user = _user(request)
    rp = rp_of(request)
    cfg = store.load()
    llmc, push = cfg["llm"], cfg["push"]
    flash = '<div class="ok">已保存</div>' if saved else ""
    body = f"""
    <h1>系统配置</h1><p class="sub">修改即时持久化到 server-data/config.json（密钥仅存服务器本地）</p>
    {flash}
    <div class="panel"><h2>LLM 语义生成</h2>
      <form method="post" action="{rp}/admin/config/save">
      <div class="grid2">
        <div><label>API Base URL（OpenAI 兼容）</label>
          <input name="llm_base_url" value="{llmc['base_url']}"></div>
        <div><label>模型</label><input name="llm_model" value="{llmc['model']}"></div>
        <div style="grid-column:1/-1"><label>API Key</label>
          <input name="llm_api_key" type="password" value="{llmc['api_key']}" placeholder="sk-…"></div>
        <div><label>单次最大 Token</label>
          <input name="llm_max_tokens" type="number" value="{llmc['max_tokens']}"></div>
        <div><label>视觉（文档步骤附带联览图，需视觉模型）</label>
          <select name="llm_vision">
            <option value="1" {'selected' if llmc.get('vision') else ''}>开启</option>
            <option value="" {'selected' if not llmc.get('vision') else ''}>关闭</option>
          </select></div>
      </div>
      <div style="margin:18px 0;display:flex;gap:10px">
        <button class="btn" type="submit" name="save" value="1">保存</button>
        <button class="btn ghost" type="submit" name="test" value="1">测试连接</button>
      </div></form>
      <div id="test-result"></div></div>

    <div class="panel"><h2>推送到 openflow</h2>
      <form method="post" action="{rp}/admin/config/save">
      <div class="grid2">
        <div><label>任务完成后自动推送</label>
          <select name="push_enabled">
            <option value="1" {'selected' if push['enabled'] else ''}>开启</option>
            <option value="" {'selected' if not push['enabled'] else ''}>关闭</option></select></div>
        <div><label>推送状态</label>
          <select name="push_status">
            <option value="draft" {'selected' if push['status'] == 'draft' else ''}>草稿（进 openflow 后台待发）</option>
            <option value="published" {'selected' if push['status'] == 'published' else ''}>直接发布上线</option></select></div>
        <div><label>文章分类</label><input name="push_category" value="{push['category']}"></div>
        <div><label>作者署名</label><input name="push_author" value="{push['author']}"></div>
        <div style="grid-column:1/-1"><label>openflow 数据目录</label>
          <input name="push_openflow_data" value="{push['openflow_data']}"></div>
      </div>
      <div style="margin-top:18px"><button class="btn">保存推送配置</button></div>
      </form>
      <p class="sub" style="margin:12px 0 0">推送为幂等覆盖：同一视频再次生成会更新 openflow 里的同 ID 文章。默认草稿态，到 openflow 后台 content-hub 里发布。</p></div>

    <div class="panel"><h2>管理员密码</h2>
      <form method="post" action="{rp}/admin/password?saved=1">
      <div class="grid2">
        <div><label>账号</label><input name="username" value="{(cfg.get('admin') or {}).get('username', 'admin')}"></div>
        <div><label>新密码</label><input name="password" type="password" required minlength="8"></div>
      </div>
      <div style="margin-top:18px"><button class="btn">更新凭据</button></div></form></div>
    """ + f"""
    <script>
    const RP = {json.dumps(rp)};
    document.querySelectorAll("form")[0].addEventListener("submit", async function(e){{
      if(e.submitter && e.submitter.name === "test"){{
        e.preventDefault();
        const fd = new FormData(this);
        fd.set("test", "1");
        const r = await fetch(RP + "/api/admin/config/test", {{method:"POST", body: fd}});
        const j = await r.json();
        document.getElementById("test-result").innerHTML = j.ok
          ? '<div class="ok">连接正常：'+j.reply+'</div>'
          : '<div class="err">失败：'+j.error+'</div>';
      }}
    }});
    </script>"""
    return page(rp, "系统配置", "config", body, user)


@router.post("/admin/config/save")
async def config_save(request: Request):
    rp = rp_of(request)
    if not _user(request):
        return RedirectResponse(rp + "/admin/login", 302)
    form = await request.form()
    store.update("llm", {
        "base_url": str(form.get("llm_base_url", "")).strip(),
        "api_key": str(form.get("llm_api_key", "")).strip(),
        "model": str(form.get("llm_model", "")).strip(),
        "max_tokens": int(form.get("llm_max_tokens") or 8192),
        "vision": bool(form.get("llm_vision")),
    })
    if "push_enabled" in form:
        store.update("push", {
            "enabled": bool(form.get("push_enabled")),
            "status": str(form.get("push_status", "draft")),
            "category": str(form.get("push_category", "ai-create")),
            "author": str(form.get("push_author", "V2HTML 引擎")),
            "openflow_data": str(form.get("push_openflow_data", "")).strip(),
        })
    return RedirectResponse(rp + "/admin/config/?saved=1", 302)


@router.post("/api/admin/config/test")
async def config_test(request: Request):
    if not _user(request):
        return JSONResponse({"ok": False, "error": "未登录"}, 401)
    form = await request.form()
    if form.get("llm_api_key") is not None:      # 先暂存表单值再测试
        store.update("llm", {
            "base_url": str(form.get("llm_base_url", "")).strip(),
            "api_key": str(form.get("llm_api_key", "")).strip(),
            "model": str(form.get("llm_model", "")).strip(),
            "max_tokens": int(form.get("llm_max_tokens") or 8192),
            "vision": bool(form.get("llm_vision")),
        })
    ok, msg = llm.test_connection()
    return JSONResponse({"ok": ok, "reply" if ok else "error": msg})


@router.post("/admin/password")
async def password_change(request: Request):
    rp = rp_of(request)
    if not _user(request):
        return RedirectResponse(rp + "/admin/login", 302)
    form = await request.form()
    auth.set_credentials(str(form.get("username", "admin")).strip() or "admin",
                         str(form.get("password", "")))
    return RedirectResponse(rp + "/admin/config/?saved=1", 302)
