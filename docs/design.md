# 工作流设计

## 目标

程序支持两个 OJ：`atcoder` 和 `cf`。

两者共享同一条主流程：

1. 从 `usergroup/<group>.json` 读取所选 OJ 的用户列表。
2. 解析并展开 `--contest` 里的查询 token。
3. 为每个用户更新一次本地缓存。
4. 仅基于缓存判断哪些用户做过展开后的目标比赛。

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

完成所有用户缓存更新后，按展开后的 contest 顺序逐个检查：

- 对命中的用户输出 `<user_id> done <contest_id>`
- 若某个比赛无人命中，输出 `no users have done <contest_id>`

这意味着单点查询、多比赛查询、区间查询本质上共享同一套缓存检查逻辑。

## 模块职责

- `src/cli.py`
  - 参数解析
  - group 文件读取
  - contest token 展开
  - 主流程调度和输出

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

- `src/oj/atcoder.py`
  - AtCoder token 规则、抓取规则、命中规则

- `src/oj/cf.py`
  - Codeforces token 规则、抓取规则、命中规则

- `src/oj/registry.py`
  - `oj` 名称到 adapter 的映射

## 文档导航

- AtCoder 细节：`docs/oj-atcoder.md`
- Codeforces 细节：`docs/oj-codeforces.md`
- 测试说明：`docs/test.md`
