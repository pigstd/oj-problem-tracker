# TODO

## 支持多 OJ（AtCoder + Codeforces）

- [x] CLI 增加 `--oj` 参数，支持 `atcoder` / `cf`
- [x] `--oj cf` 时校验 `--contest` 为纯数字
- [x] group 文件解析改为新格式：`{"atcoder": [...], "cf": [...]}`
- [x] 缓存目录拆分为 `cache/atcoder/users/` 与 `cache/cf/users/`
- [x] 缓存结构增加 `oj` 字段，并升级 `version`

## AtCoder

- [x] 保留现有 API + 403 代理回退逻辑
- [x] 保留 `from_second` 增量分页策略
- [x] 保留 `contest_id` 大小写不敏感匹配

## Codeforces

- [x] 新增 `user.status` 抓取逻辑
- [x] 过期更新时执行全量重抓（不走增量游标）
- [x] 新增 `contestId` 数值匹配逻辑

## 测试

- [x] 更新现有缓存测试以适配 OJ 维度
- [x] 新增 Codeforces 缓存行为测试（fresh skip / stale full refetch / refresh）
- [x] 新增参数与输入格式校验测试
