# Codeforces Rules

## Contest Tokens

Codeforces accepts two token forms:

- Single contest ID: `2065`
- Inclusive numeric range: `2065-2070`

Range rules:

- Both endpoints must be pure digits.
- The start number must not exceed the end number.
- The expanded result is a closed interval.

Examples:

- `2065-2067` -> `2065`, `2066`, `2067`
- Gym contests use the same numeric `contestId` rule.

## Contest Matching

After token expansion, each expanded contest is matched independently against cached submissions.

Matching rule:

- `submission.contestId == contest`

The normalized contest value is an integer.

## Fetching And Cache

- Cache path: `cache/cf/users/{user_id}.json`
- Fresh caches younger than 24 hours are reused without network access.
- Stale caches are rebuilt from page 1.
- `--refresh-cache` also triggers a full refetch.

API behavior:

- API: `https://codeforces.com/api/user.status`
- Request pacing: 1 request every 2 seconds
- Consecutive failure limit: 5
- Pagination:
  - `from` starts at 1
  - `count` is fixed at 1000
  - fetching stops when the page is empty or shorter than 1000 rows

Submissions are deduplicated by submission `id` while rebuilding the cache.
