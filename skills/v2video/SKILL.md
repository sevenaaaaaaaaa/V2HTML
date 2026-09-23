---
name: v2video
description: 逆向方向：把文章、文档、PPT 或幻灯片变成视频物料。提供两种模式——提示词包（分镜+旁白+字幕，供 Sora/Veo/可灵等视频生成工具）与 HTML 动画（可播放可录屏的单文件动效演示）。当用户要求"把这篇文章/PPT做成视频"、"生成分镜脚本"、"做动画演示视频"时使用。
version: 0.1.0
metadata:
  v2html:
    project: /Users/sevenaaaaaaa/V2HTML
---

# V2VIDEO：文章 / PPT → 视频

三个模式，按内容形态选择（用户指定模式时听用户的）：

| 模式 | 适用 | 产物 | 方法论 |
|------|------|------|--------|
| ① 提示词模式 | 实景/人物/氛围类画面 | `storyboard/`（分镜 JSON + 三家工具提示词 + 旁白 + 字幕） | `prompts/reverse-storyboard.md` |
| ② HTML 动画模式 | 文字/数据/图表/流程类内容 | `anim.html` 单文件可播放动画（可录屏成片） | `prompts/reverse-htmlanim.md` |
| ③ 视频直出 | （未来 API 接入） | — | 分镜 JSON 即预留渲染接口 |

## 执行流程

1. **读输入**：文章/文档直接读；PPT/PPTX 先提取文本（unzip pptx 读 `ppt/slides/slideN.xml`，或用 pandoc/pptx 工具）；slides.html 提取各页文字。未找到输入文件时向用户要路径。
2. **定模式**：按上方表格判断并向用户说明选择理由（一句话）。
3. **产出**（写在输入文件同目录，或用户指定目录）：
   - 模式①：`storyboard.json` + `narration.md` + `subs.srt` + `README.md`，严格按 `prompts/reverse-storyboard.md` 的数据结构与分镜规则。JSON 校验：`python3 -m json.tool storyboard.json`。
   - 模式②：`anim.html` 单文件，严格按 `prompts/reverse-htmlanim.md`（时间轴驱动、动效克制、零外部依赖、底部字幕条按 C 开关）。
4. **自检**：模式②用无头 Chrome 对 3 个时间点截图抽查（`--screenshot --window-size=1280,720` + JS 定时暂停，或改用 `?t=SEC` 参数实现定格）；模式①检查 JSON 可解析、旁白连贯成篇、每镜头提示词独立可用。
5. **交付汇报**：产物路径 + 总时长/镜头数 + 使用方法（模式①：先录旁白→逐镜头生成→对齐剪辑；模式②：浏览器打开自动播放，OBS 录屏 1280×720）。

## 质量线

- 旁白是连贯的口播稿，不是镜头说明书的拼贴。
- 画面描述具体到可画/可执行；文字与数据永远由 HTML 层承载，不依赖 AI 画面生成文字。
- 数字与观点忠实原文；二次创作需用户明确要求。
- 失败处理：输入是 PDF/PPTX 且本机无解析工具时，让用户给文字版或用 Read 工具直接读 PDF。
