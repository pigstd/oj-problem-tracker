# Web 主题维护指南

## 目标

Web UI 的主题只负责前端配色，不影响后端接口、检查流程、缓存、group 数据或运行结果。

当前支持的主题：

- `classic`：默认主题，保持项目原有视觉
- `ocean`：冷色主题
- `light`：浅色主题
- `rainbow`：彩虹主题

## 新增主题步骤

新增主题时同步修改这些位置：

1. `src/web/static/app.js`
   - 把新的 theme id 加到 `SUPPORTED_THEMES`
   - 在英文和中文 `translations` 中增加 `theme.<id>` 文案
2. `src/web/static/index.html`
   - 在 `#theme-select` 里增加 `<option value="<id>" data-theme-option="<id>" data-i18n="theme.<id>">...`
3. `src/web/static/styles.css`
   - 增加 `:root[data-theme="<id>"]` 变量覆盖块
4. `tests/test_web.py`
   - 增加 HTML、JS、CSS 的静态断言
5. `docs/frontend.md`、`docs/test.md`、`README.md`
   - 更新支持主题列表和主题数量描述

theme id 使用小写 kebab-case，例如 `forest-night`。

## 变量清单

新增主题至少检查这些变量：

- 背景：`--bg-top`、`--bg-bottom`、`--bg-glow-one`、`--bg-glow-two`、`--page-background`
- 面板：`--panel`、`--panel-strong`、`--panel-border`、`--panel-outline`
- 文字：`--text-main`、`--text-muted`、`--title-text`
- 强调色：`--accent`、`--accent-deep`、`--accent-border`、`--accent-border-strong`
- 强调色透明层：`--accent-soft`、`--accent-softer`、`--accent-selected`、`--accent-focus`、`--accent-shadow`
- 顶部控件：`--chrome-text`、`--chrome-muted`、`--chrome-border`、`--chrome-bg`、`--chrome-active-bg`、`--chrome-active-text`
- 表面层：`--surface`、`--surface-soft`、`--surface-muted`、`--surface-input`、`--surface-control`、`--surface-control-alt`
- 按钮：`--submit-button-bg`、`--button-text`
- 状态色：`--success`、`--danger`、`--warning`
- 阴影：`--shadow`

`--success`、`--danger`、`--warning` 是语义色。新增主题可以微调它们，但不要改变语义：命中仍然偏红，无命中仍然偏绿，warning/skipped 仍然偏黄。

## 对比度要求

新增主题必须保证：

- 标题在页面背景上清晰可读
- panel 内正文和表单控件可读
- 顶部 `Language` / `Theme` 控件的普通、hover、active、focus 状态都有足够对比
- `Start Check`、notice、badge、chip 在当前面板背景上可读
- 小屏换行后顶部控件不相互覆盖

## 最小模板

```css
:root[data-theme="forest-night"] {
  --bg-top: #123027;
  --bg-bottom: #1f4a3d;
  --bg-glow-one: rgba(115, 184, 139, 0.18);
  --bg-glow-two: rgba(229, 180, 96, 0.14);
  --panel: rgba(241, 248, 242, 0.96);
  --panel-strong: #fbfff9;
  --panel-border: rgba(26, 72, 54, 0.14);
  --text-main: #173429;
  --text-muted: #61766a;
  --title-text: #f8f4ea;
  --accent: #4f8f5e;
  --accent-deep: #2e6942;
  --accent-border: rgba(79, 143, 94, 0.24);
  --accent-border-strong: rgba(79, 143, 94, 0.52);
  --accent-soft: rgba(79, 143, 94, 0.12);
  --accent-softer: rgba(79, 143, 94, 0.08);
  --accent-selected: rgba(79, 143, 94, 0.15);
  --accent-focus: rgba(79, 143, 94, 0.48);
  --accent-shadow: rgba(46, 105, 66, 0.22);
  --success: #19705c;
  --danger: #98322a;
  --warning: #8d6117;
  --shadow: 0 26px 60px rgba(8, 28, 22, 0.2);
}
```

## 不做的事

- 不从后端加载主题配置
- 不允许用户输入任意 CSS
- 不让主题影响 API 请求、检查流程或缓存逻辑
