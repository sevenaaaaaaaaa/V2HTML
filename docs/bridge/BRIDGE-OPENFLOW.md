# OpenFlow 桥接指南

> ConFlow 与 OpenFlow（芭乐派入口层）的打通件。两条桥：**openflow-bridge 插件**（PHP，装在 OpenFlow 侧）与 ConFlow 内置的 openflow 推送适配器（Python，随服务端）。

## 架构

```
OpenFlow 后台「ConFlow」菜单 ──提交/查进度──▶ ConFlow API（Bearer CONFLOW_TOKEN）
AI 岗位 / 自动化画布 ──工具节点──▶ /api/plugin/conflow-bridge/{health|submit|jobs}
ConFlow 服务端 ──任务完成──▶ openflow 推送适配器 ──▶ 内容库 articles/index.json（幂等覆盖·写前备份·草稿态）
```

职责边界：插件只做入口与监控；成品交付由 ConFlow 服务端经已验证的推送适配器完成——发布链路不引入新代码路径。

## 安装（OpenFlow 侧）

1. `cp -r deploy/openflow-plugin/conflow-bridge  ~/OpenFlowDev/plugins/`（或服务器对应目录）；
2. 后台「系统 → 插件管理」启用 **conflow-bridge**（manifest 已设 `enabled_by_default: false`——文件就位后默认不加载，需手动开启才生效）；
3. 后台新菜单「ConFlow」→ 填 ConFlow 服务器地址与 API Token（服务器 `.env` 的 `CONFLOW_TOKEN`）→ 保存；
4. 提交一条视频链接验证：任务出现在列表 → done 后点开产物 → 内容库出现草稿文章。

## AI 岗位工具节点

`docs/bridge/ai-tool-schema.json` 提供 OpenAPI 式工具定义：`conflow_submit_video` / `conflow_check_job`。桥接插件的 API 路由代持密钥，AI 岗位调用不接触 token。挂接到自动化画布：在 AI 岗位的工具清单里加入上述两个端点即可（OpenFlow 侧的画布映射按其工具注册规范）。

## 验收清单

- [ ] OpenFlow 后台出现 ConFlow 菜单，配置保存后 health 返回 `configured: true`
- [ ] 后台提交视频 → ConFlow 任务列表可见 → done 后内容库出现 `conflow_<vid>` 草稿
- [ ] `POST /api/plugin/conflow-bridge/submit` 可被 AI 岗位调用并返回任务 ID
- [ ] 同一视频重复提交 → 内容库幂等覆盖（不产生重复文章）
