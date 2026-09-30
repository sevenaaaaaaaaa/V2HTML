# ConFlow 变更日志

## 0.4.0 · 2026-09-30

产品由 V2HTML 改名 **ConFlow**（目录/仓库名沿用）。

### 新增
- **P0**：API 鉴权（CONFLOW_TOKEN）；任务列表 SQLite 持久化（重启回载/中断标记）；faster-whisper 无字幕兜底（模型/后端可配）；GitHub Actions 部署通道
- **P1**：推送适配器层（openflow / WordPress / 静态目录 / Webhook，插件可扩展）；幻灯片逐页自动质检（渲染/启发式双模式）；批量与订阅（频道/播放列表展开、后台订阅管理、定时调度）；CLI 直转 `bin/conflow.py convert`（语义核心解耦为 `engine/` 包）；多语言产出（10 语言，防幻觉规则不降级）；短视频口播脚本（节拍表与 v2video storyboard 同构）
- **P2**：插件规范 v1（推送目标/新文体/主题 CSS，文件即约定）；视频直出阶段一（storyboard 渲染接口四件套）；OpenFlow 桥接插件交付件与 AI 岗位工具 schema；定制开发展示位
- 文档：README 按 OpenFlow 表述逻辑重做（架构示意图/真实截图/功能总附录）；docs/ ROADMAP · USAGE-GUIDE · PLUGIN-DEV · SERVICES · BRIDGE-OPENFLOW；MIT LICENSE

### 修复
- 幂等覆盖兼容改名前 v2html_ 旧 id；坏播放列表 500 → 回退单视频/400；多插件列表合并覆盖；服务器 python3.6 编码兼容；yt-dlp 部署时自动升级

### 已知边界
- CentOS7（glibc 2.17）原生装不上 faster-whisper（onnxruntime 需 manylinux_2_27）；B 站等站点海外机房 IP 需 cookies；OpenFlow 桥接插件待宿主侧联调；视频直出阶段二（渲染成片）未开始

## 0.2.0 · 2026-09-27 之前（V2HTML 时期）

- 视频 → 文档（四文体方法论）+ 30 主题重构型幻灯片引擎
- FastAPI 服务端 + 管理后台 + openflow 推送；ZCode 技能双形态
- 线上部署 nownexts.com/VTH（Apache 子路径 + systemd）
