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
- 不保留 hero、大段说明文案、统计卡片或其它摘要模块

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

- `OJ`
- `Group`
- `Contest Token`
- `Force refresh cache`
- `Start Check`

### OJ

- 使用单选按钮切换 `atcoder` / `cf`

### Group

- 使用下拉框选择 `usergroup/<group>.json`
- `Group` 右侧放置一个 `View` 按钮
- 若当前没有选中 group，`View` 按钮禁用

### Contest Token

- 使用紧凑的多行文本框
- 通过空白字符切分多个 token
- token 规则与 CLI 完全一致

### 错误提示

`Input` 模块底部保留两类提示：

- group 文件扫描错误
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

- `GET /api/groups/{name}`

前端会对已查看过的 group 做一次内存缓存，避免重复请求。

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
- 命中时展示命中的用户列表
- 未命中时展示 `no users have done <contest_id>`
- 若存在 warning，则在对应 contest 卡片里额外展示 `Possible same-round matches`
- warning 会列出用户以及触发 warning 的同场 sibling contest ID

`Result` 是主界面里唯一允许内部滚动的模块。若 contest 太多，由 `Result` 自己滚动，而不是整个页面滚动。

## 交互流程

### 初始化

页面加载后：

1. 请求 `GET /api/groups`
2. 填充 group 下拉框
3. 渲染 group 扫描错误
4. 若没有可用 group，则禁用提交按钮并显示错误

### 发起检查

用户点击 `Start Check` 后：

1. 读取当前 `OJ`、`Group`、`Contest Token`、`refresh_cache`
2. 调用 `POST /api/check`
3. 若成功，拿到 `run_id`
4. 轮询 `GET /api/runs/{id}`
5. 用返回的 `events` 更新 `Log`
6. 用返回的 `contest_summaries` 更新 `Result`

### 并发运行限制

当前后端限制同一时刻只能有一个运行中的检查任务。

若 `POST /api/check` 返回冲突：

- 前端会跟随当前已有的运行任务
- 不会新建第二个并发任务

## 接口依赖

当前前端依赖以下接口：

- `GET /api/groups`
  - 返回 group 名称和各 OJ 的人数摘要
- `GET /api/groups/{name}`
  - 返回指定 group 的完整用户列表
- `POST /api/check`
  - 发起一次检查任务
- `GET /api/runs/{id}`
  - 返回运行状态、最近事件、contest 精确结果和 warning 结果

## 当前实现约束

- Web 界面定位为单机 `localhost` 使用
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
- `Result` 仍然保持 contest 级展示，而不是回到用户级缓存状态展示
- Codeforces warning 继续作为附加信息展示，而不是替代精确命中结果
