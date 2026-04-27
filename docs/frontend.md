# Web 前端设计

## 目标

`oj-web.py` 提供一个本机 `localhost` 网页界面，用来承接当前项目的前端交互。

当前版本的前端设计目标是：

- 桌面端优先
- 页面主视图单屏展示
- 桌面端页面本身不出现纵向滚动
- 主界面固定为三块：`Input`、`Log`、`Result`

这里的“单屏、不滚动”目标针对常见桌面和笔记本视口。当前实现中，较小宽度会退化为纵向堆叠布局，以保证仍然可用。

## 页面结构

### 顶部标题行

- 页面顶部只保留一个标题：`OJ Problem Tracker`
- 标题后附带一个 GitHub 图标链接，跳到 repo：`https://github.com/pigstd/oj-problem-tracker`
- 标题右侧提供语言切换：`English` / `中文`
- 默认语言为英文；用户选择的语言保存在浏览器 `localStorage`
- 不直接在标题区展示完整 repo URL
- 不保留 hero、大段说明文案、统计卡片或其它摘要模块

### 语言切换

当前 Web 前端支持英文和中文两套界面文案。

规则：

- 默认语言为英文
- 语言缓存 key 为 `oj-problem-tracker.language.v1`
- 只接受 `en` 和 `zh-CN`，非法缓存值回退到英文
- 切换语言后立即更新当前页面可见文案，不需要刷新页面
- 中文模式覆盖前端可控的 UI 文案、提示、确认框、弹窗和结果区固定文案
- 后端返回的运行事件原文保持不翻译，避免前端复制后端业务语义
- 语言选择只保存在当前浏览器，不写入服务器

### 主内容区

标题下方为固定三列布局：

1. `Input`
2. `Log`
3. `Result`

当前视觉权重是：

- `Input` 偏窄，用于表单录入
- `Log` 更窄，用于显示最近事件
- `Result` 最宽，用于显示 contest 结果

桌面端主内容区占据标题以下的全部可用高度。页面本身不滚动，只有指定模块允许内部滚动。

## Input 模块

`Input` 模块负责发起一次检查任务。

当前包含以下控件：

- 标题行右侧的 `Start Check`
- `OJ`
- `Group`
- `Contest Token`
- `Contest Type`（仅 Codeforces）
- `Force refresh cache`

### OJ

- 使用单选按钮切换 `atcoder` / `cf`

### Group

当前 Web 前端的 group 完全由浏览器本地维护，不读取服务器 `usergroup/`。

当前设计：

- 使用下拉框选择浏览器 `localStorage` 中的命名 group
- `Group` 右侧放置 `View` 和 `Edit` 按钮
- 下方放置 `New`、`Import JSON`、`Delete` 按钮
- 若当前没有选中 group，则 `View`、`Edit`、`Delete` 和 `Start Check` 禁用

当前支持的 group 操作：

- 新建空 group
- 从 JSON 导入 group
- 手动编辑 group 名称
- 分别为 `atcoder` / `cf` 手动添加和删除用户
- 删除当前本地 group

JSON 导入格式沿用项目原有 group 结构：

```json
{
  "atcoder": ["alice"],
  "cf": ["tourist", "Petr"]
}
```

当前规则：

- group 只保存在当前浏览器的 `localStorage`
- Web 查询时总是把完整 `group_users` 放进请求体，不通过 group 名称回查服务器文件
- 从浏览器发起查询不会把 group 定义写入服务器硬盘
- 若所选 OJ 在当前 group 下没有用户，前端会阻止提交

### Start Check

- 放在 `Input` 模块标题行右侧
- 视觉上不再占用表单底部空间
- 提交逻辑与原来一致，仍然读取当前表单里的全部输入

### Contest Token

- 使用紧凑的多行文本框
- 通过空白字符切分多个 token
- token 规则与 CLI 完全一致

### Contest Type

只在 `cf` 被选中时显示。

当前设计：

- 默认显示一个 `Choose contest type` 折叠按钮
- 折叠按钮文案附带已选数量，例如 `Choose contest type (6 selected)`
- 点击后展开包含 `Select all`、`Clear all` 和比赛类型多选框的区域
- 默认全部选中
- 提供 `Select all` 和 `Clear all`
- 展开后不再单独形成内部滚动子区域，而是跟随整个 `Input` 模块一起滚动
- 若当前一个都不选，前端会阻止提交

当前支持的选项：

- `Div. 1`
- `Div. 2`
- `Div. 1 + 2`
- `Div. 3`
- `Div. 4`
- `Others`

语义规则：

- 这是“目标比赛过滤”而不是 warning 过滤
- 如果某个目标 contest 因类型不在选中集合而被跳过，它仍然会出现在结果里
- `Educational Codeforces Round` 在后端归类为 `Div. 2`

### 错误提示

`Input` 模块底部保留两类提示：

- 本地 group / 浏览器存储相关提示
- 表单提交或轮询过程中的错误

## Group View 弹窗

点击 `Group` 旁边的 `View` 按钮后，打开一个模态弹窗，不改变主页面三列布局。

弹窗展示内容：

- 当前 group 名称
- `atcoder` 用户列表
- `cf` 用户列表

当前规则：

- 两个 OJ 同时展示
- 用户使用 chip 列表方式显示
- 若某个 OJ 没有配置用户，显示 `No users configured.`

关闭方式：

- 点击 `Close`
- 点击遮罩
- 按 `Esc`

数据来源：

- 直接读取当前浏览器里的本地 group 数据

当前实现还会复用同一个弹窗承载编辑状态：

- `Edit` 或 `New` 会切换到 group 编辑表单
- 弹窗内可修改 group 名称
- 两个 OJ 各自有独立的用户添加区
- 现有用户以可删除的 chip 列表展示
- `Save Group` 会写回 `localStorage`

## Log 模块

`Log` 模块只展示最近的运行事件，不显示详细运行统计。

当前规则：

- 只保留最近 3 条事件
- 最新事件显示在最上方
- 头部只保留一个简洁状态 badge
- warning 事件和普通事件一起进入最近 3 条裁剪

当前状态值：

- `Idle`
- `Running`
- `Completed`
- `Failed`

`Log` 显示的是事件流的裁剪结果，不是完整日志历史。

明确不再显示以下内容：

- `Run ID`
- `Expanded Contests`
- `Users Checked`
- `User Cache Status`

## Result 模块

`Result` 模块只负责展示 contest 级别的命中结果。

当前规则：

- 按展开后的 contest 顺序展示
- 每个展开后的 contest 都单独显示
- 命中和未命中都要显示
- 被过滤掉的 contest 也要显示，但状态为 `Skipped`
- 命中时展示命中的用户列表
- 未命中时展示 `no users have done <contest_id>`
- 命中 badge 使用红色，未命中 badge 使用绿色
- `Skipped` 卡片展示识别到的比赛类型和跳过原因
- 若存在 warning，则在对应 contest 卡片里额外展示 `Possible same-round matches`
- warning 会列出用户以及触发 warning 的同场 sibling contest ID

`Result` 是主界面里主要的内部滚动区域。若 contest 太多，由 `Result` 自己滚动，而不是整个页面滚动。

补充说明：

- `Input` 模块在内容过长时由整个模块自身内部滚动
- `Contest Type` 展开后不再单独形成内部滚动子区域，而是跟随 `Input` 模块一起滚动

## 交互流程

### 初始化

页面加载后：

1. 从浏览器 `localStorage` 读取语言设置并应用界面文案
2. 从浏览器 `localStorage` 读取本地 group 列表
3. 填充 group 下拉框
4. 恢复上次选中的 group
5. 若没有可用 group，则禁用提交按钮并显示提示

### 发起检查

用户点击 `Start Check` 后：

1. 读取当前 `OJ`、`Group`、`Contest Token`、`refresh_cache`
2. 若当前是 `cf`，额外读取 `Contest Type`
3. 读取当前 group 的完整 `group_users`
4. 若所选 OJ 没有用户，则阻止提交
5. 若当前是 `cf` 且一个类型都没选，则阻止提交
6. 调用 `POST /api/check`
7. 若成功，拿到 `run_id`
8. 轮询 `GET /api/runs/{id}`
9. 用返回的 `events` 更新 `Log`
10. 用返回的 `contest_summaries` 更新 `Result`

### 并发运行限制

当前后端限制同一时刻只能有一个运行中的检查任务。

若 `POST /api/check` 返回冲突：

- 前端会跟随当前已有的运行任务
- 不会新建第二个并发任务

## 接口依赖

当前前端依赖以下接口：

- `POST /api/check`
  - 发起一次检查任务
  - 请求体必须包含 `group_users`
  - 请求体中的 `contest_types` 只对 `cf` 生效；省略时等价于全部类型
- `GET /api/runs/{id}`
  - 返回运行状态、最近事件、contest 精确结果和 warning 结果

## 当前实现约束

- Web 界面定位为单机 `localhost` 使用
- group 只存浏览器本地，不做账户同步，也不回写服务器文件
- 语言选择只存浏览器本地，不影响后端接口和检查结果
- 后端只允许一个运行中的任务
- CLI 和 Web 共用同一套检查逻辑
- 桌面端页面固定单屏
- 小屏宽度下允许退化布局，以保证可用性

## 后续迭代边界

如果后续继续改前端，默认应遵守以下约束，除非文档先被更新：

- 不新增会把页面重新撑成纵向长页面的模块
- 不恢复 `User Cache Status`
- 不把 `Log` 改回完整长列表
- 不把 group 详情直接嵌入主页面，仍然优先使用弹窗
- 不重新引入服务器 `usergroup/` 扫描与 Web group 列表接口
- `Result` 仍然保持 contest 级展示，而不是回到用户级缓存状态展示
- Codeforces warning 继续作为附加信息展示，而不是替代精确命中结果
- Codeforces 比赛类型筛选继续放在 `Input` 面板中，不单独拆成第四栏
