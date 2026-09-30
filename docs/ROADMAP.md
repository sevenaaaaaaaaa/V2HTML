# ConFlow 路线图

> 原则：先把「敢给人用」的短板补齐，再把「一个视频」变成「一条生产线」，最后把方法论沉淀成平台。
> 状态区分：**已实现**（本表勾选并注明验收证据）/ 进行中 / 规划——不把远景写成现状。
> 筛选标准：一切以「让 OpenFlow 内容库的供给更多、更稳」和「开源版永远够用」为前提。

## 待办清单（当前排序，做完一项勾一项）

1. **OpenFlow 桥接插件宿主联调**（P1 收尾）— 交付件已就绪（deploy/openflow-plugin/ + docs/bridge/），待 OpenFlow 侧排期安装与端到端联调。
2. **线上 demo 扩到 6–8 条**（P0 余项）— 补多主题/多文体/多语言成品，撑起示例作品区门面。
3. **视频直出 · 阶段二（渲染成片）**（P2）— Remotion / 云端渲染选型；storyboard.json 接口已冻结。
4. **一键安装体验**（P0 余项）— Docker 镜像与起步体验（评估中）。
5. **插件规范 v2**（P2）— 钩子（doc_done / before_push / after_push）、视频源注册、插件管理页。
6. **定制开发案例补录**（P2 展示位）— 首个定制项目落地后回填 docs/SERVICES.md。

## P0 · 工程还债（2026-09-30 完成）

- [x] **API 写接口鉴权** — 公网部署设置 `CONFLOW_TOKEN` 后，所有写接口要求 Bearer 认证；未设置时 `/api/health` 的 `auth` 字段如实显示 `false`。
  验收：带 token 创建任务 200 / 不带 401；health 显示 `auth:true`。
- [x] **任务列表持久化** — SQLite（`server-data/jobs.db`），每步执行日志即落盘；重启全量回载，被打断的任务标记为可重试的错误态。
  验收：建任务 → 重启服务 → 任务仍在列表、进度与产物链接完整。
- [x] **无字幕视频兜底** — 内置 faster-whisper 转写（无 torch 依赖，CPU int8 可跑，PyAV 自带解码）；模型大小 `CONFLOW_WHISPER_MODEL` 可调（默认 `small`），后端可用 `CONFLOW_WHISPER_BACKEND` 强制指定。
  验收：本地（macOS）无字幕视频切片全链路真实转写通过。
  ⚠️ 已知边界：faster-whisper 依赖的 onnxruntime 对 Python 3.12 只发 manylinux_2_27+ wheel，CentOS7（glibc 2.17）等老系统原生装不上——此类环境下无字幕视频明确报错，待 Docker 镜像（P0）解决；新系统自建不受影响。
- [ ] **视频源凭据支持** — yt-dlp cookies 通用配置（B 站等站点对海外/机房 IP 有风控，无登录 cookies 会拒绝流访问；实测美国服务器抓 B 站失败，本机正常）。
  验收：服务器配置 cookies 后，B 站视频可完整走通 fetch → 产出。
- [ ] **线上 demo 扩到 6–8 条** — 补 B 站源、多主题成品种类，让示例作品区撑起门面。
- [ ] **一键安装体验** — Docker 镜像与 `pip install conflow-server` 级别的起步体验（评估中）。

## P1 · 从工具到生产线（1–2 个月）

- [x] **批量与订阅** — 频道 / 播放列表 URL 在前台与 API 直接展开为任务队列（flat 元数据、按产物与任务双去重）；订阅源后台可管理，调度线程每 15 分钟轮转，新视频自动建任务；`/api/batch/expand` 只展开预览。
  验收：本地展开真实频道（3Blue1Brown）15 条元数据；TestClient 全流程通过（批量创建 / 去重 / 订阅 check-toggle-delete / 鉴权）。
- [x] **多语言产出** — `engine/generate.py` 语言指令注入（zh 默认免指令；en/ja/ko/es/fr/de/pt/ru/ar 硬性要求全产出一个语言，代码/专名保留原文），doc 与 slides 同语言，`html lang` 同步；前台表单 / CLI `--language` / API `language` 三处入口。
  验收：引擎级断言（英文指令进 doc/slides 的 system prompt、`<html lang="en">`、默认中文无指令）；线上真实 LLM 英文任务验收（见部署记录）。
- [x] **短视频脚本版** — 新方法论 `prompts/script-short.md`（45–90s 节拍表：秒数按语速实算、口播词/画面提示/屏幕大字逐拍给出，数字只来自已核对的 doc.md；节拍字段与 reverse-storyboard 的 storyboard.json 同构），engine `gen_short_script`（语言贯通），CLI `--script` / API `script: true` / 前台勾选，产物 `output/<id>/script.md`。
  验收：引擎级断言（脚本 prompt 含方法论文案 + 语言指令；产物含节拍表/衔接 v2video 结构）；API script 参数入队、admin 产物链接按文件存在条件显示；线上真实 LLM 任务验收（见部署记录）。
- [ ] **OpenFlow 桥接插件** — 以 OpenFlow PluginSystem 形态提供入口：插件挂后台菜单与配置页（服务器地址 + token），提交/轮询走 ConFlow HTTP API，任务完成后经 openflow cron 心跳原生写入内容库（替代文件级 pushof，走内部 API 更干净）。ThirdC 若有同类插件机制则复用同一桥接模式。
  验收：openflow 后台出现 ConFlow 页面，提交任务、查看进度、成品直接进入 content-hub。
- [x] **CLI 直转模式** — `bin/conflow.py convert <url>`：fetch → 转写 → 判定 → 文档 → 幻灯片 → 质检一条命令全链路，配置走 `CONFLOW_LLM_*` / `~/.conflow/config.json`；语义核心解耦为 `engine/` 包（llm provider 模式：服务端注入 store 热配置，CLI 用 env，插件可程序化注入），服务端与 CLI 共用。
  验收：本地真实 E2E（真实抓取 + mock LLM 端点）73s 出 doc + slides + render 质检；服务端回归（health/jobs）通过；频道链接可批量逐个转换。
- [x] **推送适配器抽象** — `server/pushers.py` 统一调度，官方适配 openflow（原有）/ WordPress / 静态目录 / Webhook 四种目标，后台可切换与配置；新目标约 30 行适配器即可注册。
  验收：本地 mock 服务四适配器全通过（含 openflow 幂等与备份、webhook secret 头、WP Basic 认证）；线上以 static 目标实推一个已完成任务验证后切回 openflow。
- [x] **质量基线自动化** — 引擎内置 `?qc=1` 自检（每页缩放比/溢出 JSON 报告），服务端产出后自动质检：有 headless Chrome 走真实渲染判定，无浏览器回退内容量预算启发式（按真实成品校准）；任务详情逐页标注 ok/warn/fail 与原因，不拦截任务。
  验收：故意超载页两种模式均检出（render：压缩至 36% 标红；heuristic：998 字符超预算）；四套真实成品全过；无浏览器/旧引擎 deck 回退链验证。

## P2 · 平台化

- [x] **视频直出 · 阶段一（渲染接口）** — `engine/storyboard.py`：doc.md → LLM 产出 `storyboard/storyboard.json`（shots 含 narration/scene/motion/on_screen 与 sora/veo/kling 提示词，即渲染器输入接口），narration.md / subs.srt / README 确定性派生；CLI `--storyboard` / API `storyboard: true` / 前台「🎞 分镜包」勾选。
  验收：线上真实 LLM 任务（见部署记录）；**阶段二（渲染成片：Remotion / 云端渲染选型）未开始**，接口已按其输入冻结。
- [x] **正式插件规范 v1** — `plugins/<id>/` + `plugin.json` 文件即约定：push.py 注册推送目标（目标名=目录名）、doc-<type>.md 注册新文体、themes.css 注入主题（manifest.themes 声明即接受）；失败隔离（单插件挂不拖垮主流程）。文档 docs/PLUGIN-DEV.md，官方示例 plugins/example-receipt/。
  验收：本地加载示例插件 → 推送目标清单含 example-receipt、示例回执落盘；钩子规范（doc_done/before_push 等）为 v2 候选。
- [x] **OpenFlow AI 岗位工具 / 桥接插件交付件** — `deploy/openflow-plugin/conflow-bridge/`（按宿主 PluginSystem v2 真实约定：register_admin_menu/register_admin_page/register_api_route + DATA_DIR json 配置，php -l 通过）；工具节点 `/api/plugin/conflow-bridge/{health|submit|jobs}`，schema 见 docs/bridge/ai-tool-schema.json（conflow_submit_video / conflow_check_job）；发布链路复用已验证的 openflow 推送适配器。
  验收：PHP 语法校验通过 + 约定与宿主真实插件（userloop-bridge/example-plugin）逐条对齐；**宿主侧安装与端到端联调待 OpenFlow 侧排期**。
- [x] **定制开发展示位** — docs/SERVICES.md：三个服务包（私有视频源接入 / 企业内容库对接 / 专属文体与主题）+ 工作方式（能用插件解决的优先指导自做）+ 案例展示位；README 开源章节收口。
  验收：展示位就绪；真实案例待首个项目落地后补验收记录。

## 不做（与定位冲突，明确拒绝）

- **多人协作 / 团队空间** — Studio 层是本地工具，账户体系是 OpenFlow（入口层）的事；矩阵账号互通已覆盖。
- **SaaS 化托管** — 低门槛自建是核心卖点；托管会拖垮部署简单性与数据自主权。
- **在线幻灯片编辑器** — 产出物是「可直接上线」的成品而非草稿；改主题/文案改文件或 URL 参数即可。

---

维护：芭乐派 · 提案与讨论请开 Issue。
