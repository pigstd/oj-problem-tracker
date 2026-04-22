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

## Contest Type Filtering

Codeforces API does not expose a direct division field that can be used for the current CLI and web filters.
The project therefore classifies contests from the contest title stored in `contest.list`.

Current filter buckets:

- `div1`
- `div2`
- `div1+2`
- `div3`
- `div4`
- `others`

Current title rules:

- `Educational Codeforces Round` is treated as `div2`
- Titles containing both `Div. 1` and `Div. 2` are treated as `div1+2`
- Otherwise the first matching bucket among `Div. 4`, `Div. 3`, `Div. 2`, `Div. 1` is used
- Titles with none of those markers fall into `others`

Entry points:

- CLI: `--only div1 div2`
- Web: `contest_types` array in `POST /api/check`

Default behavior:

- Omitting the filter is equivalent to selecting all buckets
- The filter only decides whether the target contest is checked or skipped
- If a contest is skipped, it still appears in the final result with status `skipped`
- If a contest is kept, same-round warning detection still remains active even when the sibling contest belongs to another bucket

## Same-Round Warning

Codeforces may have adjacent contests such as Div.1 / Div.2 that start at the same time but use different contest IDs.

Current behavior keeps exact matching unchanged, but adds a warning-only path:

- Target contest `p` is still considered an exact hit only when `submission.contestId == p`
- For warning detection, only `p-1` and `p+1` are inspected
- If one of those adjacent contests exists and has the same `startTimeSeconds` as `p`, it is treated as a same-round sibling contest
- If a user did not hit `p` exactly but did submit in a same-round sibling contest, the program emits a warning

This warning does not become a normal hit.

The same-round warning path is independent from the title-based target filter:

- the filter applies to the requested target contest
- the warning path still inspects `p-1` and `p+1` purely by `startTimeSeconds`
- so a kept `div1` target may still emit a warning from a same-round `div2` sibling contest

Current output rule:

- If nobody exactly hit `p`, the program still prints `no users have done <p>`
- If some users only hit same-round sibling contests, the program also prints yellow warning lines for those users

Gym contests do not participate in this same-round warning logic.

## Fetching And Cache

- Cache path: `cache/cf/users/{user_id}.json`
- Fresh caches younger than 24 hours are reused without network access.
- Stale caches are rebuilt from page 1.
- `--refresh-cache` also triggers a full refetch.
- A shared contest catalog cache is stored at `cache/cf/contests.json`
- The contest catalog cache is refreshed at most once per 24 hours
- `--refresh-cache` also forces a contest catalog refresh

API behavior:

- API: `https://codeforces.com/api/user.status`
- Contest catalog API: `https://codeforces.com/api/contest.list?gym=false`
- Request pacing: 1 request every 2 seconds
- Consecutive failure limit: 5
- Pagination:
  - `from` starts at 1
  - `count` is fixed at 1000
  - fetching stops when the page is empty or shorter than 1000 rows

Submissions are deduplicated by submission `id` while rebuilding the cache.
The contest catalog stores contest IDs, contest titles, and `startTimeSeconds`.
Those fields support both same-round warning detection and title-based contest type classification.
