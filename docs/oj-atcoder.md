# AtCoder Rules

## Contest Tokens

AtCoder accepts two token forms:

- Single contest ID: `abc403`
- Inclusive range with the same prefix: `abc403-abc405`

Range rules:

- Both endpoints must end with a numeric suffix.
- The non-numeric prefix must match, ignoring case.
- The start number must not exceed the end number.
- Expansion preserves the left endpoint prefix text and uses the widest numeric width from the two endpoints.

Examples:

- `abc403-abc405` -> `abc403`, `abc404`, `abc405`
- `ABC001-abc003` -> `ABC001`, `ABC002`, `ABC003`

## Contest Matching

After token expansion, each expanded contest is matched independently against cached submissions.

Matching rule:

- `submission.contest_id.lower() == contest.lower()`

## Fetching And Cache

- Cache path: `cache/atcoder/users/{user_id}.json`
- Fresh caches younger than 24 hours are reused without network access.
- Stale caches are updated incrementally from `next_from_second`.
- `--refresh-cache` rebuilds the cache from `from_second=0`.

API behavior:

- Primary API: `https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions`
- Proxy fallback after HTTP 403:
  - `https://r.jina.ai/http://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions`
- Request pacing: 1 request per second
- Consecutive failure limit: 5

Cache payload fields specific to AtCoder:

- `next_from_second`
- `submissions`

Submissions are deduplicated by submission `id` during incremental merges.
