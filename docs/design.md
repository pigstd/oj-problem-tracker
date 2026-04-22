# 工作流设计

## 目标

程序支持两个 OJ：`atcoder` 和 `cf`。

两者共享同一条主流程：

1. 解析 group 输入源，并拿到所选 OJ 的用户列表。
2. 解析并展开 `--contest` 里的查询 token。
3. 对支持的 OJ，先把展开后的比赛按“目标比赛类型”做筛选或标记跳过。
4. 为本轮仍需检查的用户更新一次本地缓存。
5. 按展开后的目标比赛做精确命中检查。
6. 对支持的 OJ 追加 warning 级别的补充判定。

当前 group 输入源规则：

- CLI 兼容 `usergroup/<group>.json`
- CLI 也支持任意 JSON 文件、inline JSON 字符串、以及显式传入 `atcoder` / `cf` 用户列表
- Web 不再读取服务器 `usergroup/`，而是由浏览器把当前 group 的完整用户列表放进请求体
- Web 的 group 定义只存浏览器 `localStorage`，不会为查询流程临时写回服务器硬盘

## Contest Token 工作流

`-c/--contest` 接收一个或多个 token。每个 token 都先交给对应 OJ adapter 处理：

1. `src/cli.py` 读取原始 token 列表。
2. 对每个 token 调用 `adapter.expand_contest_token(token)`。
3. adapter 把单点或区间展开成单个比赛列表。
4. CLI 按输入顺序把这些结果拼接成最终的 contest 列表。
5. 后续流程只处理单个比赛，不再区分这些比赛来自单点还是区间。

示例：

```bash
python3 oj-problem-tracker.py --oj cf -c 2065 2067-2069 -g example
```

展开结果等价于：

```text
[2065, 2067, 2068, 2069]
```

当前实现不会对展开后的结果做跨 token 去重。

## 目标比赛类型筛选

当前只有 Codeforces 支持目标比赛类型筛选。

共享规则：

- CLI 通过 `--only` 传入一个或多个类型，例如 `--only div1 div2`
- 若未传 `--only`，则等价于 `--only all`
- Web 端只在 `cf` 模式下显示比赛类型多选区域
- 被筛掉的比赛不会参与精确命中检查，但仍然会保留在结果里，状态为 `skipped`

Codeforces 当前支持的类型：

- `div1`
- `div2`
- `div1+2`
- `div3`
- `div4`
- `others`

补充规则：

- `Educational Codeforces Round` 归类为 `div2`
- 同场 warning 仍然只看开始时间相同的相邻比赛，不受目标比赛类型筛选影响
- 也就是说，若目标比赛本身被保留检查，则它仍然可能通过一个不同类型的同场 sibling contest 触发 warning

## 运行流程

### 阶段 1：缓存更新

对所选 OJ 的每个用户执行：

1. 读取 `cache/{oj}/users/{user_id}.json`
2. 若缓存不存在，则初始化抓取
3. 若缓存存在且不足 24 小时，则跳过网络更新
4. 若缓存过期或传入 `--refresh-cache`：
   - AtCoder 从 `next_from_second` 继续增量抓取
   - Codeforces 从第一页重新全量抓取
5. 写回缓存文件

### 阶段 2：比赛命中检查

完成所有用户缓存更新后，按展开后的 contest 顺序逐个处理：

- 若某个 contest 在筛选阶段被标记为 `skipped`，则输出 skip 事件并写入 skip 结果
- 若某个 contest 仍然需要检查，则继续执行精确命中和 warning 判定

- 对命中的用户输出 `<user_id> done <contest_id>`
- 若某个比赛无人命中，输出 `no users have done <contest_id>`
- 对支持 warning 判定的 OJ，可额外输出 warning 结果

这意味着单点查询、多比赛查询、区间查询本质上共享同一套缓存检查逻辑。

当前只有 Codeforces 会追加 warning 判定：

- 先按 `contestId` 做精确匹配
- 若目标比赛没有被某个用户精确命中，则再检查相邻比赛是否属于同一开赛场次
- 若相邻同场比赛被做过，则输出 warning，但不把它当作正常命中

## 模块职责

- `src/cli.py`
  - 参数解析
  - group 输入源解析与校验
  - contest token 展开
  - 主流程调度和输出

- `src/core/groups.py`
  - group JSON 结构校验
  - 兼容旧的 group 文件读取
  - 从内存 group payload 中提取所选 OJ 用户列表

- `src/core/cache.py`
  - 缓存读写
  - 缓存格式校验
  - 更新时间判断

- `src/core/tracker.py`
  - 用户缓存更新编排
  - 单个 contest 的缓存命中判断

- `src/oj/base.py`
  - `OJAdapter` 抽象接口
  - 包括 `validate_contest`、`expand_contest_token`、`update_submissions`、`submission_matches_contest`
  - 也包括可选的 `select_target_contests` 钩子，用于把展开后的比赛标记为检查或跳过

- `src/oj/atcoder.py`
  - AtCoder token 规则、抓取规则、命中规则

- `src/oj/cf.py`
  - Codeforces token 规则、抓取规则、命中规则
  - Codeforces 比赛目录缓存
  - Codeforces 比赛标题到类型桶的归类逻辑
  - Codeforces 同场 warning 判定

- `src/oj/registry.py`
  - `oj` 名称到 adapter 的映射

- `src/web/server.py`
  - 校验 Web 请求体中的 `group_users`
  - 启动后台检查任务
  - 提供运行轮询接口

## 文档导航

- AtCoder 细节：`docs/oj-atcoder.md`
- Codeforces 细节：`docs/oj-codeforces.md`
- Web 前端设计：`docs/frontend.md`
- 测试说明：`docs/test.md`

当前 Web 界面的布局、交互和接口依赖以 `docs/frontend.md` 为准。
