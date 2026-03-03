根据 design.md 中的设计，完成该项目的全部功能（不包括后面的其他设计）。

实现时必须覆盖以下细节：

- `contest_id` 大小写不敏感比较。
- “做过”定义为有提交即可，不要求 AC。
- 找到某个用户做过后，继续检查其他用户；只跳过该用户的剩余提交。
- API 每次调用后 sleep 1 秒（全局 1 req/s）。
- 优先调用官方 API，若返回 403 则回退到只读代理继续获取数据。
- 分页使用 `from_second = max(epoch_second) + 1`，空列表停止。
- API 请求失败重试；连续 5 次失败则报错并退出。
- `group` 文件不存在、JSON 非法、`users` 缺失或为空时，报错并退出。
- 输出格式：
  - 检查用户前：`checking user <user_id> ...`
  - 命中用户：`<user_id> done <contest_id>`
  - 全部未命中：`no users have done <contest_id>`
