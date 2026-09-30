# ConFlow 插件开发指南（v1）

> 设计原则：**文件即约定，放进去就生效**——与 OpenFlow PluginSystem 同一心智，无注册中心、无钩子框架，重启/重跑即加载。核心功能永不因插件缺失受影响。

## 1. 插件结构

```
plugins/
└── my-plugin/
    ├── plugin.json      ← 必须，元信息
    ├── push.py          ← 可选，注册一个推送目标（目标名 = 目录名）
    ├── doc-<type>.md    ← 可选，注册新文体写作法（<type> 即 doc_type 取值）
    └── themes.css       ← 可选，注入幻灯片引擎的主题样式
```

`plugin.json`：

```json
{
  "name": "我的插件",
  "version": "0.1.0",
  "description": "做什么用",
  "author": "you",
  "themes": ["mytheme"]        // 可选：声明本插件提供的主题名
}
```

## 2. 三类扩展点

### 2.1 推送目标（push.py）

实现一个函数，即成为「系统配置 → 推送目标」里的新选项（目标名 = 插件目录名）：

```python
def push(workdir, meta, doc_md, cfg) -> dict:
    # workdir: output/<video_id>/ 目录；meta: 标题/作者/来源链接等
    # doc_md: 已核对定稿的 Markdown；cfg: push 配置段
    return {"id": "...", "slug": "...", "status": "written",
            "path": "...", "title": "..."}   # 至少含 id/slug/status
```

参考实现：`plugins/example-receipt/`（回执落盘，约 20 行）与内置 `server/pushers.py` 四适配器。

### 2.2 新文体（doc-<type>.md）

放一个 `doc-interview.md`，用户即可 `doc_type: interview` 指定（自动判定暂只覆盖内置四文体，插件文体手工指定）。写法对齐 `prompts/doc-science.md`：结构 + 质量线 + 防幻觉规则（数字逐字核对、补全显式标注、观点归属分离）。

### 2.3 主题（themes.css + plugin.json.themes）

```css
[data-theme="mytheme"]{
  --bg:#0d0a1a; --bg-soft:#171232; --ink:#f4f2ff;
  --muted:#9d97c9; --accent:#8b7cf6; --accent-2:#4dd6ff;
  --line:rgba(255,255,255,.10); --body-bg:#07060d;
}
/* 需要时对组件整段覆写，见 templates/slides.html 主题预设区 */
```

`plugin.json` 的 `themes` 数组声明主题名后，服务端建任务即接受 `theme: "mytheme"`；CSS 会在建 deck 时自动注入 `<head>`。

## 3. 加载时机与失败隔离

- 服务端：启动时加载一次；CLI：每次运行加载一次；均缓存。
- 单个插件加载失败（语法错/缺清单）→ 打印告警并跳过，主流程不受影响。
- 修改插件后：服务端重启生效，CLI 下次运行生效。

## 4. 规范路线（v2 候选）

- 钩子：`doc_done` / `before_push` / `after_push`（对齐 OpenFlow 的 filter/action）；
- 视频源注册：非 yt-dlp 源的适配器接口；
- 插件管理后台页（启停 + 健康展示）。

提案与讨论：仓库 Issue。
