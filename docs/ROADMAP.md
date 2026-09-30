# ConFlow 路线图

> 原则：先把「敢给人用」的短板补齐，再把「一个视频」变成「一条生产线」，最后把方法论沉淀成平台。
> 状态区分：**已实现**（本表勾选并注明验收证据）/ 进行中 / 规划——不把远景写成现状。
> 筛选标准：一切以「让 OpenFlow 内容库的供给更多、更稳」和「开源版永远够用」为前提。

## 待办清单（当前排序，做完一项勾一项）

1. **短视频脚本版**（P1）— doc.md 衍生口播脚本，衔接 v2video 分镜链路，打通「视频→文章→视频物料」环。
2. **OpenFlow 桥接插件**（P1）— PluginSystem 挂菜单/配置页，走 ConFlow API + openflow 心跳原生写内容库。
3. **线上 demo 扩到 6–8 条**（P0 余项）— 补多主题/多文体成品，撑起示例作品区门面。
4. **一键安装体验**（P0 余项）— Docker 镜像与起步体验（评估中）。
5. **视频直出 / 正式插件规范 / AI 岗位工具 / 定制开发案例**（P2，见下）。

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
- [ ] **短视频脚本版** — doc.md 衍生口播脚本（复用口播节拍写作法），衔接 v2video 分镜链路。
  验收：一次任务可选产出「文章 / 幻灯片 / 短视频脚本」三件套。
- [ ] **OpenFlow 桥接插件** — 以 OpenFlow PluginSystem 形态提供入口：插件挂后台菜单与配置页（服务器地址 + token），提交/轮询走 ConFlow HTTP API，任务完成后经 openflow cron 心跳原生写入内容库（替代文件级 pushof，走内部 API 更干净）。ThirdC 若有同类插件机制则复用同一桥接模式。
  验收：openflow 后台出现 ConFlow 页面，提交任务、查看进度、成品直接进入 content-hub。
- [x] **CLI 直转模式** — `bin/conflow.py convert <url>`：fetch → 转写 → 判定 → 文档 → 幻灯片 → 质检一条命令全链路，配置走 `CONFLOW_LLM_*` / `~/.conflow/config.json`；语义核心解耦为 `engine/` 包（llm provider 模式：服务端注入 store 热配置，CLI 用 env，插件可程序化注入），服务端与 CLI 共用。
  验收：本地真实 E2E（真实抓取 + mock LLM 端点）73s 出 doc + slides + render 质检；服务端回归（health/jobs）通过；频道链接可批量逐个转换。
- [x] **推送适配器抽象** — `server/pushers.py` 统一调度，官方适配 openflow（原有）/ WordPress / 静态目录 / Webhook 四种目标，后台可切换与配置；新目标约 30 行适配器即可注册。
  验收：本地 mock 服务四适配器全通过（含 openflow 幂等与备份、webhook secret 头、WP Basic 认证）；线上以 static 目标实推一个已完成任务验证后切回 openflow。
- [x] **质量基线自动化** — 引擎内置 `?qc=1` 自检（每页缩放比/溢出 JSON 报告），服务端产出后自动质检：有 headless Chrome 走真实渲染判定，无浏览器回退内容量预算启发式（按真实成品校准）；任务详情逐页标注 ok/warn/fail 与原因，不拦截任务。
  验收：故意超载页两种模式均检出（render：压缩至 36% 标红；heuristic：998 字符超预算）；四套真实成品全过；无浏览器/旧引擎 deck 回退链验证。

## P2 · 平台化（一个季度维度）

- [ ] **视频直出** — 分镜 JSON → 渲染成片。先走已验证的 HTML 动画路径，Remotion/服务端渲染选型评估中。
- [ ] **正式插件规范** — manifest + 钩子（文体注册 / 主题注册 / 推送注册 / 视频源注册），对齐 OpenFlow PluginSystem 心智。
- [ ] **OpenFlow AI 岗位工具** — ConFlow API 注册为 OpenFlow 自动化画布的工具节点，「内容供给」成为 AI 岗位可调度的能力。
- [ ] **定制开发展示位** — 2–3 个真实案例（私有视频源接入、企业内容库对接、专属文体写作法）；只做对接与定制，核心功能永不收费。

## 不做（与定位冲突，明确拒绝）

- **多人协作 / 团队空间** — Studio 层是本地工具，账户体系是 OpenFlow（入口层）的事；矩阵账号互通已覆盖。
- **SaaS 化托管** — 低门槛自建是核心卖点；托管会拖垮部署简单性与数据自主权。
- **在线幻灯片编辑器** — 产出物是「可直接上线」的成品而非草稿；改主题/文案改文件或 URL 参数即可。

---

维护：芭乐派 · 提案与讨论请开 Issue。
