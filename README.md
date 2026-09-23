# V2HTML — 视频 ⇄ HTML 双向内容引擎

> 把一条 YouTube 视频变成可上线的高质量文档与讲课幻灯片；再把任意文章 / PPT 逆向变成可录制的动画视频。
> 名字的由来：**视频 → HTML**（文档、幻灯片、动画都是 HTML），**HTML → 视频**（逆向）。

## 产品愿景

1. **正向：视频 → 内容资产**
   输入 YouTube 链接，通过「字幕/语音的语义分析 + 关键帧的画面分析」，产出可读性、实用性、逻辑性都很高的：
   - 教程类视频 → **教程文档**（可复现的步骤、命令、避坑清单）
   - 科普类视频 → **科普文章**（心智模型、分层深度、FAQ）
   - 普通口播视频 → **评论文章**（论点、论据、反方视角、独立判断）
   - 其他类型 → 适配性文章（访谈纪要、演讲实录、评测…）
   - 同步产出**重构型幻灯片**：不是视频截图拼贴，而是按内容逻辑重新组织、用统一设计系统重新设计的 HTML 幻灯片。

2. **逆向：文章 / PPT → 视频**（三阶段路线）
   - **提示词模式**（已支持）：生成分镜脚本 + 每个镜头的视频生成提示词（Sora / Veo / Kling / 即梦等通用格式）、旁白脚本、字幕文件。拿去任何视频生成工具即可。
   - **HTML 动画模式**（已支持）：生成自包含的 HTML 动态演示——按时间轴播放的动效场景（motion graphics），可直接投屏讲课，或录屏成片。
   - **视频直出模式**（规划中）：接入视频生成 API 的渲染管线，接口已在 `prompts/reverse-storyboard.md` 的分镜数据结构中预留。

## 架构：脚本管确定性，Agent 管语义

```
YouTube URL
   │
   ▼
bin/v2h.py fetch        ── 代理探测、拉取元数据/字幕/音频（yt-dlp）
bin/v2h.py transcribe   ── 字幕优先，缺失时调用本地 Whisper（若有）
bin/v2h.py frames       ── ffmpeg 场景切变抽帧 + 生成联览图(contact sheet)
   │
   ▼  output/<video_id>/
   │     meta.json  transcript.md  frames/  sheet.jpg
   ▼
语义核心（两种形态，产物同构）
   ├─ 客户端：ZCode 技能 /v2html —— Agent 按 prompts/*.md 方法论执行
   └─ 服务端：server/ —— 把同一套方法论组装为 LLM API 调用（可部署、可远程调用）
   │
   ▼
doc.md / doc.html / slides.html
   │
   ▼
Agent（/v2video 技能）   ── 逆向：storyboard.json + 提示词包 / HTML 动画
```

**分工原则**：下载、转写、抽帧是确定性工作，交给脚本保证可复现；分类、结构重组、写作、幻灯片设计是语义工作。客户端形态由 Agent 亲自执行；服务端形态由 `server/generate.py` 把方法论提示词发给任意 OpenAI 兼容 LLM API 执行。`frames/` 里的帧只作为**画面参考与素材**（图表、演示画面可被精选嵌入），绝不等于幻灯片本身。

## 双形态：客户端 ⇄ 服务端

### 客户端形态（本机，推荐日常用）

- ZCode 里说一句话或 `/v2html <url>`，Agent 调用 `bin/v2h.py` + `prompts/` 方法论，亲自完成语义工作
- 无需 API Key、无需联网服务（除视频下载），产物质量上限最高（Agent 可逐帧核对事实）

### 服务端形态（可部署在服务器/家庭 NAS）

```bash
# 本机启动
pip3 install --user fastapi "uvicorn[standard]"   # 或 pip install -r requirements.txt
bash server/run.sh                                 # http://0.0.0.0:8400

# Docker 部署（推荐，自带 ffmpeg 与 Python3.12）
V2HTML_LLM_API_KEY=你的key docker compose up -d --build
```

**已部署实例**：nownexts.com 服务器（172.96.253.73，宝塔 Apache），
`/www/wwwroot/V2HTML`（与 openflow 站点同级）→ Docker 端口 `127.0.0.1:8410`，
入口 **https://nownexts.com/VTH/**（Apache extension conf 反代，见下），
LLM 复用 openflow 的 DeepSeek key（`data/ai-config.json`）。

环境变量（写入部署目录 `.env`，chmod 600）：

| 变量 | 说明 |
|---|---|
| `V2HTML_LLM_API_KEY` | **必填**。任何 OpenAI 兼容接口的 key |
| `V2HTML_LLM_BASE_URL` | 默认智谱 GLM；可换 DeepSeek `https://api.deepseek.com/v1` 等 |
| `V2HTML_LLM_MODEL` | 默认 `glm-4.7`；需支持长输出 |
| `V2HTML_LLM_MAX_TOKENS` | 默认 8192（DeepSeek 上限） |
| `V2HTML_PROXY` | 访问 YouTube 的代理；海外服务器直连即可（已验证 204） |
| `V2HTML_TOKEN` | 公网部署建议设置；POST /api/jobs 需 Bearer 认证 |
| `V2HTML_BIND` | Docker 端口映射，默认 `127.0.0.1:8410` |

**子路径反代（Apache）**：在 `/www/server/panel/vhost/apache/extension/<域名>/v2html.conf` 写入——

```apache
ProxyPass /VTH/ http://127.0.0.1:8410/
ProxyPassReverse /VTH/ http://127.0.0.1:8410/
<Location "/VTH/">
    Require all granted
</Location>
```

UI/API 已全部相对路径化，根路径与任意子路径反代通用。若站点在 Cloudflare 后面：
应用已对所有响应发 `Cache-Control: no-store`；改动 UI 后建议在 CF 后台 Purge 一次。

接口：`POST /api/jobs`（`{url, doc_type: auto|tutorial|science|commentary|other, theme, max_frames}`）·
`GET /api/jobs/{id}`（进度与产物链接）· `GET /api/health` · Web UI 在 `/`。
产物与客户端完全同构（`output/<video_id>/doc.md + slides.html`），slides.html 依旧离线可用、30 主题可切换。
注意：① 服务端容器内无 Whisper，无字幕视频需装（`mlx-whisper`/`faster-whisper`）；
② 未配置可用 LLM key 时任务在素材就绪后报错/暂停，中间产物不丢；
③ 服务器磁盘余量需关注（每条视频缓存约 10–50MB）。

## 使用

```bash
# 一次性准备（在 ZCode 中说一句话即可，技能会自动调用脚本）：
#   “用 v2html 把 https://youtu.be/xxxx 转成教程文档和幻灯片”

# 或手动分步：
python3 bin/v2h.py fetch <youtube-url>       # 元数据 + 字幕 + 抽帧
python3 bin/v2h.py transcribe <video_id>     # 仅当没有字幕时需要（需本地 Whisper）
python3 bin/v2h.py status                    # 查看已有产物
```

Agent 侧技能（安装后全局可用）：

| 技能 | 作用 |
|------|------|
| `/v2html <url> [类型]` | 视频 → 分类判定 → 文档 + 幻灯片 |
| `/v2video <文章/幻灯片路径> [模式]` | 文章/PPT → 分镜提示词包 / HTML 动画 |

### 幻灯片主题库（30 个预设，四大家族）

改 `<html data-theme="...">` 即换肤，放映中按 `T` 键循环预览：
- **自研基础**：`science`（夜紫·科普）/ `tutorial`（深空蓝）/ `commentary`（暖纸衬线）
- **产品风致敬**（键名无商标，只取气质）：`terracotta`（≈Claude 暖陶土）/ `paper-doc`（≈Notion）/ `prism`（≈Arc）/ `aurora`（≈Linear）
- **当代平面风格**（组件级差异）：`glass` 毛玻璃 / `memphis` 孟菲斯 / `vapor` 蒸汽波 / `riso` 孔版印刷 / `broadsheet` 报刊编辑 / `luxe` 奢侈极简 / `academia` 暗色学院 / `y2k` 千禧 / `blueprint` 蓝图 / `pop` 波普漫画
- **设计运动**：`zen` 日式极简 / `swiss` 国际主义 / `bauhaus` 包豪斯 / `deco` 装饰艺术 / `brutal` 新粗野 / `kraft` 牛皮纸实物 / `neon` 赛博未来
- **设计系统收编**：`geist` / `carbon` / `ant` / `tdesign` / `arco` / `material3`

明细与选型见 `prompts/slides.md`。

## 目录

```
bin/v2h.py            单入口 CLI：fetch / transcribe / frames / status
prompts/              方法论提示词包（Agent 的操作手册，可持续迭代）
  classify.md             视频类型判定规则
  doc-tutorial.md         教程文档写作法
  doc-science.md          科普文章写作法
  doc-commentary.md       评论文章写作法
  doc-other.md            其他类型适配法
  slides.md               重构型幻灯片设计系统
  reverse-storyboard.md   逆向①：分镜 + 视频生成提示词（提示词模式）
  reverse-htmlanim.md     逆向②：HTML 动画模式
templates/slides.html 幻灯片运行时（自包含、离线可用的设计系统）
skills/               技能源码（bin/install-skills.sh 安装到 ~/.agents/skills）
output/<video_id>/    每条视频一个产物目录
```

## 依赖

- 必需：`ffmpeg`、`python3`（自带）
- `yt-dlp`：`pip3 install --user yt-dlp`（或 `brew install yt-dlp`，建议定期升级）
- 代理：自动探测 `http_proxy` 环境变量及本机 6152/6153/7890 等常见端口（Surge/Clash）
- 本地 Whisper（可选，字幕缺失时的兜底）：`pip3 install --user mlx-whisper`（Apple Silicon 推荐）或 `openai-whisper`

## 安装技能到全局

```bash
bash bin/install-skills.sh    # 把 skills/ 同步到 ~/.agents/skills/，之后 /v2html /v2video 全局可用
```
