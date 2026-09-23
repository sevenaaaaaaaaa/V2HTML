---
name: v2html
description: 把 YouTube 等视频转换为高质量文档与重构型幻灯片。当用户给出视频链接（YouTube/B站等）并希望转成教程文档、科普文章、评论文章、纪要或幻灯片/PPT 时使用。
version: 0.1.0
metadata:
  v2html:
    project: /Users/sevenaaaaaaa/V2HTML
---

# V2HTML：视频 → 文档 + 幻灯片

把一条视频变成「可读性、实用性、逻辑性」都过关的文章与一套**重构型** HTML 幻灯片（不是截图拼贴）。项目根目录：`/Users/sevenaaaaaaa/V2HTML`。

## 执行流程

### 第 1 步：素材准备（脚本）

```bash
cd /Users/sevenaaaaaaa/V2HTML
python3 bin/v2h.py fetch '<视频URL>'        # 注意 URL 加引号（zsh 会吞 ?）
python3 bin/v2h.py status                   # 查看产物：id / 时长 / 帧数 / transcript
```

fetch 自动完成：代理探测 → 下载 480p 视频 → 字幕（人工优先）→ 场景抽帧（默认 24 帧）→ 联览图 → transcript.md。产物在 `output/<video_id>/`。

- 若无字幕（fetch 输出会提示）：`python3 bin/v2h.py transcribe <video_id>`（需本地 whisper，未装时按提示安装）。
- 用户指定"帧多一点/少一点"：`python3 bin/v2h.py frames <video_id> --max-frames 36`。

### 第 2 步：类型判定

按 `prompts/classify.md`：通读 `output/<id>/transcript.md` + 看 `sheet.jpg`（用 Read 工具直接看图）+ `*.info.json` 的章节信息，判定 tutorial / science / commentary / other，置信度低时读 3-5 张 `frames/` 单帧确认。**把判定结果和理由告诉用户。**

### 第 3 步：写文档 doc.md

按对应方法论执行：`prompts/doc-tutorial.md`（教程）、`prompts/doc-science.md`（科普）、`prompts/doc-commentary.md`（评论）、`prompts/doc-other.md`（其他）。写到 `output/<id>/doc.md`。

硬性要求：数字/命令/专名与 `transcript.json` 逐字核对；需要独有视觉信息（图表/界面）时用 Read 看对应单帧（文件名含时间戳）；补全内容必须用标注体系显式区分。

### 第 4 步：做幻灯片 slides.html

按 `prompts/slides.md` 执行。把 `templates/slides.html` 复制到 `output/<id>/slides.html`，改 THEME 变量与 `<title>`，替换示例页为实际内容（跟随论证结构而非时间轴；嵌入 ≤4 张含独有信息的帧，相对路径 `frames/...`）。

### 第 5 步：自检与交付

1. 截图抽查（见下方"质检"）：封面 + 最密一页 + 含图页，确认无溢出截断。
2. 向用户汇报：判定类型 → doc.md 与 slides.html 路径 → 文档核心结构一览（TL;DR 级别 3 句话）→ 幻灯片页数。给出打开方式：`open output/<id>/slides.html`（→ 翻页，O 总览，F 全屏，P 导出 PDF）。

## 质检（截图）

```bash
# 优先用 Playwright 的 headless shell（完整版 Chrome for Testing 反复强杀后会卡死）：
HS=$(find ~/Library/Caches/ms-playwright -maxdepth 4 -type f -name "chrome-headless-shell" 2>/dev/null | sort | tail -1)
"$HS" --headless --disable-gpu --screenshot=/tmp/slide-3.png \
  --window-size=1280,720 --hide-scrollbars \
  'file:///Users/sevenaaaaaaa/V2HTML/output/<id>/slides.html?shot=3'
# 注意：macOS 无 timeout 命令；若 Chrome 进程挂起（0% CPU 不退出），pkill -9 后改用 headless_shell
```

没有 Chrome 时跳过截图，改为提醒用户自查。发现溢出/截断就精简该页文字后重新截图确认。

## 边界与失败处理

- URL 未加引号导致 zsh 报 `no matches found`：加引号重试。
- YouTube 限流 429：脚本已带重试；仍失败则等 30 秒重跑 fetch；只差字幕时改用 transcribe。
- 视频无信息密度（纯娱乐）：按 doc-other.md 产出短文档并说明。
- 用户只要文档不要幻灯片（或反之）：跳过对应步骤，不要多问。
- 语言：文档与幻灯片默认用中文（原文术语保留英文），用户指定其他语言时听用户的。
