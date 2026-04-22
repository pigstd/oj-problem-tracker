# 测试说明

## 运行方式

```bash
python3 -m unittest discover -s tests -v
```

当前自动化测试集中在 `tests/test_cache.py`。
目前还包括 `tests/test_check_service.py` 和 `tests/test_web.py`。

## 当前覆盖范围

### 缓存更新

- AtCoder 新用户建缓存
- AtCoder 24 小时内跳过更新
- AtCoder 增量更新时去重
- AtCoder `--refresh-cache` 强制从 0 重抓
- Codeforces 新用户建缓存
- Codeforces 24 小时内跳过更新
- Codeforces 过期后全量重抓
- Codeforces `--refresh-cache` 强制全量重抓
- Codeforces contest.list 目录缓存创建
- Codeforces contest.list 目录缓存 24 小时内跳过刷新
- Codeforces contest.list 目录缓存过期后刷新
- Codeforces `--refresh-cache` 强制刷新比赛目录缓存

### Contest Token 解析与展开

- `--contest` 多值解析
- Codeforces 单点 token 校验
- Codeforces 区间 token 展开
- Codeforces 非法区间拒绝
- AtCoder 单点 token 校验
- AtCoder 同前缀区间展开
- AtCoder 跨前缀或反向区间拒绝

### 命中判定与 CLI 编排

- AtCoder contest 匹配大小写不敏感
- Codeforces contest 匹配 `contestId` 数值相等
- Codeforces 同场 sibling warning 判定
- 单点与区间混合输入时，每个用户缓存只更新一次
- 展开后的 contest 顺序与 CLI 输入顺序一致
- 每个展开后的 contest 都输出独立结果

### 输出

- `checking user ...`
- `updating cache for ...`
- `cache hit, skip update for ...`
- 命中结果红色输出
- 无命中结果绿色输出
- warning 结果黄色输出
- 错误信息输出到 stderr

## 后续可以补的测试

- AtCoder 403 后切代理
- API 连续失败 5 次的错误路径
- 缓存文件字段损坏时的错误路径
- 帮助信息中区间说明的断言
