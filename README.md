# oj-problem-tracker

A tool for ACM team coaches to check whether team members have submitted in one or more target contests.

Supported OJ: AtCoder and Codeforces.

## Requirements

- Python 3.10+

## Group Inputs

The project accepts the same group JSON structure everywhere:

```json
{
  "atcoder": ["user1", "user2", "user3"],
  "cf": ["tourist", "Petr"]
}
```

Web UI behavior:

- The web page does not read server-side `usergroup/` files anymore.
- Groups are created, imported, edited, and deleted in the browser.
- The current browser stores them in `localStorage` and sends `group_users` with each check request.
- Querying from the web UI does not write group definitions back to server disk.

CLI group input modes:

- Legacy file mode: `-g/--group example` reads `usergroup/example.json`
- Arbitrary JSON file: `--group-json-file path/to/group.json`
- Inline JSON string: `--group-json '{"atcoder":["alice"],"cf":["tourist"]}'`
- Explicit user lists: `--atcoder-user alice bob --cf-user tourist`

For inline modes, `--group-name` controls the display label shown in results.

## Usage

Run the localhost web UI:

```bash
python3 oj-web.py
```

Then create or import a group in the browser before starting a check.

Check AtCoder users in a group for explicit contests:

```bash
python3 oj-problem-tracker.py --oj atcoder -c abc403 abc404 -g example
```

Check Codeforces users in a group for an inclusive contest range:

```bash
python3 oj-problem-tracker.py --oj cf -c 2065-2068 -g example
```

Check only selected Codeforces contest types:

```bash
python3 oj-problem-tracker.py --oj cf -c 2065 2067-2070 -g example --only div1 div2
```

Check only Educational / Div. 2 style Codeforces rounds:

```bash
python3 oj-problem-tracker.py --oj cf -c 2065-2090 -g example --only div2
```

Check AtCoder users in a group for an inclusive contest range:

```bash
python3 oj-problem-tracker.py --oj atcoder -c abc403-abc406 -g example
```

Mix single contests and ranges in one command:

```bash
python3 oj-problem-tracker.py --oj atcoder -c abc403 abc404-abc406 -g example
```

Another mixed Codeforces example:

```bash
python3 oj-problem-tracker.py --oj cf -c 2065 2067-2070 2088 -g example
```

Gym contests work the same way because Codeforces still matches on numeric `contestId`:

```bash
python3 oj-problem-tracker.py --oj cf -c 104059 104060-104062 -g example
```

Check users from an arbitrary JSON file without using `usergroup/`:

```bash
python3 oj-problem-tracker.py --oj atcoder -c abc403 --group-json-file ./team.json
```

Check users from inline JSON:

```bash
python3 oj-problem-tracker.py --oj cf -c 2065 --group-json '{"atcoder":[],"cf":["tourist","Petr"]}' --group-name inline-team
```

Check users from explicit CLI user lists:

```bash
python3 oj-problem-tracker.py --oj atcoder -c abc403-abc406 --group-name local-demo --atcoder-user alice bob charlie
```

Force refresh cache:

```bash
python3 oj-problem-tracker.py --oj atcoder -c abc403 abc404-abc406 -g example --refresh-cache
```

Show command help:

```bash
python3 oj-problem-tracker.py --help
```

Contest token rules:

- `--contest` accepts one or more tokens.
- A token can be a single contest ID such as `2065` or `abc403`.
- You can use `-` to express an inclusive contest range.
- For Codeforces, numeric ranges such as `100-200` and `2065-2070` are supported.
- For AtCoder, ranges use the same prefix plus numeric suffix, such as `abc300-abc305`.
- Tokens are expanded in input order and checked one contest at a time after caches are refreshed.

Codeforces contest type filter rules:

- `--only` is supported only when `--oj cf`.
- If `--only` is omitted, the program behaves as if all Codeforces contest types are selected.
- Supported values are `div1`, `div2`, `div1+2`, `div3`, `div4`, and `others`.
- `Educational Codeforces Round` is treated as `div2`.
- The filter applies to target contests only. Same-round warning detection still works for kept contests.

Web UI notes:

- Before the first run, create or import a local group in the browser.
- The page defaults to English and supports switching between `English` and `中文`.
- The selected language is stored in browser `localStorage`.
- The page supports `Classic`, `Ocean`, `Light`, and `Rainbow` themes, with the selected theme stored in browser `localStorage`.
- The page stores groups in browser `localStorage`, not in server-side `usergroup/`.
- `View`, `Edit`, `New`, `Import JSON`, and `Delete` all operate on local browser groups.
- In the `cf` form, the page shows a `Contest Type` multi-select area.
- It supports `Select all` and `Clear all`.
- If no Codeforces contest type is selected, the page blocks submission.

## APIs

- AtCoder submissions API (primary):
  - `https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions?user={user_id}&from_second={from_second}`
- AtCoder proxy fallback (used when primary returns HTTP 403):
  - `https://r.jina.ai/http://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions?user={user_id}&from_second={from_second}`
- Codeforces submissions API:
  - `https://codeforces.com/api/user.status?handle={handle}&from={from}&count={count}`

Request pacing:

- AtCoder: 1 request per second
- Codeforces: 1 request per 2 seconds

## Cache Behavior

- Cache path:
  - AtCoder: `cache/atcoder/users/{user_id}.json`
  - Codeforces: `cache/cf/users/{user_id}.json`
- If cache directories do not exist, they are created automatically.
- If a user's cache file does not exist, it is created automatically by full fetch.
- Default minimum update interval is 24 hours (`86400` seconds).
- If cache is fresh (less than 24 hours), the program skips network update and uses local cache.
- If cache is stale (24 hours or more):
  - AtCoder updates from `next_from_second`.
  - Codeforces performs full refetch from page 1.
- `--refresh-cache` always forces refresh.
- When checking multiple contests or contest ranges, each user's cache is still updated only once per run.

## Output

- Per user start: `checking user <user_id> ...`
- Cache update in progress: `updating cache for <user_id> ...`
- Cache hit without update: `cache hit, skip update for <user_id>`
- For each contest, a hit is printed as `<user_id> done <contest_id>`
- If nobody in the group has done a contest, print `no users have done <contest_id>`
- If a target contest is filtered out, print `skip <contest_id>: ...`
- For Codeforces, same-round sibling matches are shown as warning lines and do not become normal hits

In the web UI, filtered-out contests are kept in `Result` with status `Skipped`.

## Design Docs

- Overall workflow: `docs/design.md`
- Web frontend layout: `docs/frontend.md`
- Web theme customization: `docs/themes.md`
- AtCoder rules: `docs/oj-atcoder.md`
- Codeforces rules: `docs/oj-codeforces.md`
- Test guide: `docs/test.md`

## Test

Run automated tests:

```bash
python3 -m unittest discover -s tests -v
```

Detailed test guide: `docs/test.md`
