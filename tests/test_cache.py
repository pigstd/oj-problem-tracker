import datetime
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from src.core.checks import CheckEvent
from src.cli import ANSI_GREEN, ANSI_RED, ANSI_RESET, ANSI_YELLOW, main, parse_args, run
from src.core import cache as cache_store
from src.core.groups import load_group_users
from src.core import tracker as tracker_service
from src.core.errors import TrackerError
from src.oj.atcoder import AtCoderAdapter
from src.oj import cf as cf_module
from src.oj.cf import CodeforcesAdapter


def _iso_utc_hours_ago(hours: int) -> str:
    """Return a UTC timestamp string shifted backward by the requested hours."""
    timestamp = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
    return timestamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _cache_payload(
    oj: str,
    user_id: str,
    last_updated_at: str,
    submissions: list[dict],
    next_from_second: int | None = None,
):
    """Build a cache payload fixture matching the project's on-disk format."""
    payload = {
        "version": cache_store.CACHE_VERSION,
        "oj": oj,
        "user_id": user_id,
        "last_updated_at": last_updated_at,
        "submissions": submissions,
    }
    if oj == "atcoder":
        payload["next_from_second"] = 0 if next_from_second is None else next_from_second
    return payload


def _contest_catalog_payload(last_updated_at: str, contests: list[dict]) -> dict:
    """Build a Codeforces contest catalog cache payload for tests."""
    return {
        "version": cf_module.CONTEST_CATALOG_CACHE_VERSION,
        "oj": "cf",
        "last_updated_at": last_updated_at,
        "contests": contests,
    }


class CacheBehaviorTest(unittest.TestCase):
    """Verify cache refresh behavior for AtCoder and Codeforces adapters."""

    def setUp(self) -> None:
        """Create isolated cache roots and adapter instances for each test."""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original_cache_root = cache_store.CACHE_ROOT
        cache_store.CACHE_ROOT = Path(self.tmpdir.name) / "cache"

        self.atcoder = AtCoderAdapter()
        self.cf = CodeforcesAdapter()

        cache_store.ensure_cache_dir_exists("atcoder")
        cache_store.ensure_cache_dir_exists("cf")

    def tearDown(self) -> None:
        """Restore the original cache root and remove temporary files."""
        cache_store.CACHE_ROOT = self.original_cache_root
        self.tmpdir.cleanup()

    def test_atcoder_create_cache_for_new_user(self) -> None:
        """Verify a missing AtCoder cache is created from fetched submissions."""
        def fake_fetch(user_id: str, from_second: int):
            self.assertEqual(user_id, "alice")
            if from_second == 0:
                return [{"id": 1, "epoch_second": 100, "contest_id": "abc100"}]
            if from_second == 101:
                return []
            self.fail(f"unexpected from_second={from_second}")

        self.atcoder._fetch_submissions_with_retry = fake_fetch
        cache = tracker_service.update_user_cache(self.atcoder, "alice", refresh_cache=False)

        self.assertEqual(cache["next_from_second"], 101)
        self.assertEqual(len(cache["submissions"]), 1)
        self.assertTrue(cache_store.get_cache_file_path("atcoder", "alice").exists())

    def test_atcoder_skip_update_within_interval(self) -> None:
        """Verify fresh AtCoder caches skip network refresh and reuse local data."""
        payload = _cache_payload(
            oj="atcoder",
            user_id="bob",
            last_updated_at=_iso_utc_hours_ago(1),
            next_from_second=42,
            submissions=[{"id": 11, "epoch_second": 41, "contest_id": "abc001"}],
        )
        cache_store.write_user_cache("atcoder", "bob", payload)

        called = {"value": False}

        def fake_fetch(_: str, __: int):
            called["value"] = True
            return []

        self.atcoder._fetch_submissions_with_retry = fake_fetch
        cache = tracker_service.update_user_cache(self.atcoder, "bob", refresh_cache=False)

        self.assertFalse(called["value"])
        self.assertEqual(cache["next_from_second"], 42)
        self.assertEqual(len(cache["submissions"]), 1)

    def test_atcoder_skip_update_prints_yellow_cache_hit_status(self) -> None:
        """Verify fresh caches emit the yellow cache-hit status line."""
        payload = _cache_payload(
            oj="atcoder",
            user_id="bob",
            last_updated_at=_iso_utc_hours_ago(1),
            next_from_second=42,
            submissions=[{"id": 11, "epoch_second": 41, "contest_id": "abc001"}],
        )
        cache_store.write_user_cache("atcoder", "bob", payload)

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            cache = tracker_service.update_user_cache(self.atcoder, "bob", refresh_cache=False)

        self.assertEqual(cache["next_from_second"], 42)
        self.assertEqual(
            stdout.getvalue(),
            f"{ANSI_YELLOW}cache hit, skip update for bob{ANSI_RESET}\n",
        )

    def test_atcoder_incremental_update_and_dedup(self) -> None:
        """Verify stale AtCoder caches merge new pages while deduplicating submission IDs."""
        payload = _cache_payload(
            oj="atcoder",
            user_id="carol",
            last_updated_at=_iso_utc_hours_ago(48),
            next_from_second=10,
            submissions=[{"id": 1, "epoch_second": 9, "contest_id": "abc001"}],
        )
        cache_store.write_user_cache("atcoder", "carol", payload)

        def fake_fetch(user_id: str, from_second: int):
            self.assertEqual(user_id, "carol")
            if from_second == 10:
                return [
                    {"id": 1, "epoch_second": 10, "contest_id": "abc001"},
                    {"id": 2, "epoch_second": 12, "contest_id": "abc002"},
                ]
            if from_second == 13:
                return []
            self.fail(f"unexpected from_second={from_second}")

        self.atcoder._fetch_submissions_with_retry = fake_fetch
        cache = tracker_service.update_user_cache(self.atcoder, "carol", refresh_cache=False)

        self.assertEqual(cache["next_from_second"], 13)
        self.assertEqual([s["id"] for s in cache["submissions"]], [1, 2])

    def test_atcoder_refresh_cache_rebuilds_from_zero(self) -> None:
        """Verify refresh mode rebuilds an AtCoder cache from the initial cursor."""
        payload = _cache_payload(
            oj="atcoder",
            user_id="dave",
            last_updated_at=_iso_utc_hours_ago(1),
            next_from_second=20,
            submissions=[{"id": 9, "epoch_second": 19, "contest_id": "abc001"}],
        )
        cache_store.write_user_cache("atcoder", "dave", payload)

        def fake_fetch(user_id: str, from_second: int):
            self.assertEqual(user_id, "dave")
            if from_second == 0:
                return [{"id": 101, "epoch_second": 7, "contest_id": "abc777"}]
            if from_second == 8:
                return []
            self.fail(f"unexpected from_second={from_second}")

        self.atcoder._fetch_submissions_with_retry = fake_fetch
        cache = tracker_service.update_user_cache(self.atcoder, "dave", refresh_cache=True)

        self.assertEqual(cache["next_from_second"], 8)
        self.assertEqual([s["id"] for s in cache["submissions"]], [101])

    def test_atcoder_create_cache_prints_yellow_update_status(self) -> None:
        """Verify cache refreshes emit the yellow updating status line."""
        def fake_fetch(user_id: str, from_second: int):
            self.assertEqual(user_id, "erin")
            if from_second == 0:
                return [{"id": 1, "epoch_second": 100, "contest_id": "abc100"}]
            if from_second == 101:
                return []
            self.fail(f"unexpected from_second={from_second}")

        self.atcoder._fetch_submissions_with_retry = fake_fetch
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            cache = tracker_service.update_user_cache(self.atcoder, "erin", refresh_cache=False)

        self.assertEqual(cache["next_from_second"], 101)
        self.assertEqual(
            stdout.getvalue(),
            f"{ANSI_YELLOW}updating cache for erin ...{ANSI_RESET}\n",
        )

    def test_cf_create_cache_for_new_user(self) -> None:
        """Verify a missing Codeforces cache is created from the first fetched page."""
        calls: list[tuple[int, int]] = []

        def fake_fetch(handle: str, from_index: int, count: int):
            self.assertEqual(handle, "tourist")
            calls.append((from_index, count))
            if from_index == 1:
                return [{"id": 11, "contestId": 2065, "creationTimeSeconds": 1700000000}]
            self.fail(f"unexpected from={from_index}")

        self.cf._fetch_status_page_with_retry = fake_fetch
        cache = tracker_service.update_user_cache(self.cf, "tourist", refresh_cache=False)

        self.assertEqual(calls, [(1, 1000)])
        self.assertEqual([s["id"] for s in cache["submissions"]], [11])
        self.assertNotIn("next_from_second", cache)
        self.assertTrue(cache_store.get_cache_file_path("cf", "tourist").exists())

    def test_cf_skip_update_within_interval(self) -> None:
        """Verify fresh Codeforces caches skip network refresh and reuse local data."""
        payload = _cache_payload(
            oj="cf",
            user_id="petr",
            last_updated_at=_iso_utc_hours_ago(1),
            submissions=[{"id": 9, "contestId": 1000, "creationTimeSeconds": 10}],
        )
        cache_store.write_user_cache("cf", "petr", payload)

        called = {"value": False}

        def fake_fetch(_: str, __: int, ___: int):
            called["value"] = True
            return []

        self.cf._fetch_status_page_with_retry = fake_fetch
        cache = tracker_service.update_user_cache(self.cf, "petr", refresh_cache=False)

        self.assertFalse(called["value"])
        self.assertEqual([s["id"] for s in cache["submissions"]], [9])

    def test_cf_stale_cache_full_refetch(self) -> None:
        """Verify stale Codeforces caches are rebuilt from a full refetch."""
        payload = _cache_payload(
            oj="cf",
            user_id="neal",
            last_updated_at=_iso_utc_hours_ago(48),
            submissions=[{"id": 1, "contestId": 1000, "creationTimeSeconds": 10}],
        )
        cache_store.write_user_cache("cf", "neal", payload)

        def fake_fetch(handle: str, from_index: int, count: int):
            self.assertEqual(handle, "neal")
            self.assertEqual((from_index, count), (1, 1000))
            return [{"id": 2, "contestId": 2065, "creationTimeSeconds": 20}]

        self.cf._fetch_status_page_with_retry = fake_fetch
        cache = tracker_service.update_user_cache(self.cf, "neal", refresh_cache=False)

        self.assertEqual([s["id"] for s in cache["submissions"]], [2])

    def test_cf_refresh_cache_forces_refetch(self) -> None:
        """Verify refresh mode always triggers a full Codeforces refetch."""
        payload = _cache_payload(
            oj="cf",
            user_id="benq",
            last_updated_at=_iso_utc_hours_ago(1),
            submissions=[{"id": 10, "contestId": 1000, "creationTimeSeconds": 10}],
        )
        cache_store.write_user_cache("cf", "benq", payload)

        called = {"value": 0}

        def fake_fetch(handle: str, from_index: int, count: int):
            self.assertEqual(handle, "benq")
            called["value"] += 1
            self.assertEqual((from_index, count), (1, 1000))
            return [{"id": 99, "contestId": 3000, "creationTimeSeconds": 999}]

        self.cf._fetch_status_page_with_retry = fake_fetch
        cache = tracker_service.update_user_cache(self.cf, "benq", refresh_cache=True)

        self.assertEqual(called["value"], 1)
        self.assertEqual([s["id"] for s in cache["submissions"]], [99])

    def test_cf_prepare_run_creates_contest_catalog_cache_for_new_catalog(self) -> None:
        """Verify prepare_run creates the shared contest catalog cache when missing."""
        calls = {"value": 0}

        def fake_fetch_contests():
            calls["value"] += 1
            return [
                {"id": 2065, "startTimeSeconds": 100},
                {"id": 2066, "startTimeSeconds": 100},
            ]

        self.cf._fetch_contests_with_retry = fake_fetch_contests
        self.cf.prepare_run(refresh_cache=False)

        self.assertEqual(calls["value"], 1)
        self.assertEqual(
            self.cf.find_warning_matches([{"contestId": 2066}], 2065),
            [2066],
        )
        self.assertTrue(self.cf._get_contest_catalog_cache_file_path().exists())

    def test_cf_prepare_run_emits_status_before_refreshing_contest_catalog(self) -> None:
        """Verify prepare_run reports contest-catalog refresh before fetching contest.list."""
        call_order: list[tuple[str, str]] = []

        def fake_fetch_contests():
            call_order.append(("fetch", "contest.list"))
            return [
                {"id": 2065, "startTimeSeconds": 100},
                {"id": 2066, "startTimeSeconds": 100},
            ]

        self.cf._fetch_contests_with_retry = fake_fetch_contests
        self.cf.prepare_run(
            refresh_cache=False,
            status_callback=lambda kind, message: call_order.append((kind, message)),
        )

        self.assertEqual(
            call_order,
            [
                ("updating_contest_catalog", "updating contest catalog for cf ..."),
                ("fetch", "contest.list"),
            ],
        )

    def test_cf_prepare_run_raises_when_catalog_refresh_fails_without_cache(self) -> None:
        """Verify prepare_run fails closed when contest.list cannot be fetched and no cache exists."""
        reported_statuses: list[tuple[str, str]] = []

        def fake_fetch_contests():
            raise TrackerError("contest.list unavailable")

        self.cf._fetch_contests_with_retry = fake_fetch_contests

        with self.assertRaises(TrackerError) as ctx:
            self.cf.prepare_run(
                refresh_cache=False,
                status_callback=lambda kind, message: reported_statuses.append((kind, message)),
            )

        self.assertIn("no cached catalog is available", str(ctx.exception))
        self.assertEqual(
            reported_statuses,
            [("updating_contest_catalog", "updating contest catalog for cf ...")],
        )

    def test_cf_prepare_run_uses_cached_catalog_when_refresh_fails(self) -> None:
        """Verify prepare_run falls back to the cached catalog when refresh retries are exhausted."""
        catalog_file = self.cf._get_contest_catalog_cache_file_path()
        catalog_file.write_text(
            json.dumps(
                _contest_catalog_payload(
                    _iso_utc_hours_ago(48),
                    [
                        {"id": 2065, "startTimeSeconds": 100},
                        {"id": 2066, "startTimeSeconds": 100},
                    ],
                )
            ),
            encoding="utf-8",
        )
        reported_statuses: list[tuple[str, str]] = []

        def fake_fetch_contests():
            raise TrackerError("contest.list unavailable")

        self.cf._fetch_contests_with_retry = fake_fetch_contests
        self.cf.prepare_run(
            refresh_cache=False,
            status_callback=lambda kind, message: reported_statuses.append((kind, message)),
        )

        self.assertEqual(
            self.cf.find_warning_matches([{"contestId": 2066}], 2065),
            [2066],
        )
        self.assertEqual(reported_statuses[0], ("updating_contest_catalog", "updating contest catalog for cf ..."))
        self.assertEqual(reported_statuses[1][0], "contest_catalog_warning")
        self.assertIn("using cached catalog", reported_statuses[1][1])

    def test_cf_prepare_run_continues_when_catalog_cache_write_fails(self) -> None:
        """Verify prepare_run keeps the in-memory catalog when persisting it fails."""
        reported_statuses: list[tuple[str, str]] = []

        def fake_fetch_contests():
            return [
                {"id": 2065, "startTimeSeconds": 100},
                {"id": 2066, "startTimeSeconds": 100},
            ]

        self.cf._fetch_contests_with_retry = fake_fetch_contests
        self.cf._write_contest_catalog_cache = lambda cache_data: (_ for _ in ()).throw(OSError("disk full"))
        self.cf.prepare_run(
            refresh_cache=False,
            status_callback=lambda kind, message: reported_statuses.append((kind, message)),
        )

        self.assertEqual(
            self.cf.find_warning_matches([{"contestId": 2066}], 2065),
            [2066],
        )
        self.assertFalse(self.cf._get_contest_catalog_cache_file_path().exists())
        self.assertEqual(reported_statuses[0], ("updating_contest_catalog", "updating contest catalog for cf ..."))
        self.assertEqual(reported_statuses[1][0], "contest_catalog_warning")
        self.assertIn("continuing with in-memory catalog", reported_statuses[1][1])

    def test_cf_prepare_run_skips_catalog_refresh_within_interval(self) -> None:
        """Verify fresh contest catalog caches are reused without another API request."""
        catalog_file = self.cf._get_contest_catalog_cache_file_path()
        catalog_file.write_text(
            json.dumps(
                _contest_catalog_payload(
                    _iso_utc_hours_ago(1),
                    [
                        {"id": 2065, "startTimeSeconds": 100},
                        {"id": 2066, "startTimeSeconds": 100},
                    ],
                )
            ),
            encoding="utf-8",
        )

        called = {"value": False}

        def fake_fetch_contests():
            called["value"] = True
            return []

        self.cf._fetch_contests_with_retry = fake_fetch_contests
        self.cf.prepare_run(refresh_cache=False)

        self.assertFalse(called["value"])
        self.assertEqual(
            self.cf.find_warning_matches([{"contestId": 2066}], 2065),
            [2066],
        )

    def test_cf_prepare_run_refreshes_stale_catalog_cache(self) -> None:
        """Verify stale contest catalog caches are replaced by freshly fetched contest data."""
        catalog_file = self.cf._get_contest_catalog_cache_file_path()
        catalog_file.write_text(
            json.dumps(
                _contest_catalog_payload(
                    _iso_utc_hours_ago(48),
                    [
                        {"id": 2065, "startTimeSeconds": 100},
                        {"id": 2066, "startTimeSeconds": 200},
                    ],
                )
            ),
            encoding="utf-8",
        )

        called = {"value": 0}

        def fake_fetch_contests():
            called["value"] += 1
            return [
                {"id": 2065, "startTimeSeconds": 300},
                {"id": 2066, "startTimeSeconds": 300},
            ]

        self.cf._fetch_contests_with_retry = fake_fetch_contests
        self.cf.prepare_run(refresh_cache=False)

        self.assertEqual(called["value"], 1)
        self.assertEqual(
            self.cf.find_warning_matches([{"contestId": 2066}], 2065),
            [2066],
        )

    def test_cf_prepare_run_force_refreshes_catalog_cache(self) -> None:
        """Verify refresh mode forces a contest catalog refetch even when the cache is fresh."""
        catalog_file = self.cf._get_contest_catalog_cache_file_path()
        catalog_file.write_text(
            json.dumps(
                _contest_catalog_payload(
                    _iso_utc_hours_ago(1),
                    [
                        {"id": 2065, "startTimeSeconds": 100},
                        {"id": 2066, "startTimeSeconds": 100},
                    ],
                )
            ),
            encoding="utf-8",
        )

        called = {"value": 0}

        def fake_fetch_contests():
            called["value"] += 1
            return [
                {"id": 2065, "startTimeSeconds": 500},
                {"id": 2066, "startTimeSeconds": 500},
            ]

        self.cf._fetch_contests_with_retry = fake_fetch_contests
        self.cf.prepare_run(refresh_cache=True)

        self.assertEqual(called["value"], 1)
        self.assertEqual(
            self.cf.find_warning_matches([{"contestId": 2066}], 2065),
            [2066],
        )

    def test_cf_find_warning_matches_checks_both_adjacent_contests(self) -> None:
        """Verify warning matching inspects both adjacent contests when start times match."""
        self.cf._contest_start_times = {
            2064: 100,
            2065: 100,
            2066: 100,
        }

        warning_matches = self.cf.find_warning_matches(
            [{"contestId": 2064}, {"contestId": 2066}],
            2065,
        )

        self.assertEqual(warning_matches, [2064, 2066])


class InputValidationTest(unittest.TestCase):
    """Verify CLI-facing validation and contest matching helpers."""

    def setUp(self) -> None:
        """Create an isolated working directory with a temporary usergroup folder."""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original_cwd = Path.cwd()
        os.chdir(self.tmpdir.name)
        Path("usergroup").mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        """Restore the original working directory and remove temporary files."""
        os.chdir(self.original_cwd)
        self.tmpdir.cleanup()

    def test_load_group_users_new_format(self) -> None:
        """Verify the current group file format loads the requested OJ users."""
        group_file = Path("usergroup") / "example.json"
        group_file.write_text(
            json.dumps({"atcoder": ["alice"], "cf": ["tourist", "Petr"]}),
            encoding="utf-8",
        )

        at_users = load_group_users("example", "atcoder")
        cf_users = load_group_users("example", "cf")

        self.assertEqual(at_users, ["alice"])
        self.assertEqual(cf_users, ["tourist", "Petr"])

    def test_load_group_users_rejects_old_users_field(self) -> None:
        """Verify the legacy single-list group format is rejected."""
        group_file = Path("usergroup") / "legacy.json"
        group_file.write_text(json.dumps({"users": ["alice"]}), encoding="utf-8")

        with self.assertRaises(TrackerError):
            load_group_users("legacy", "atcoder")

    def test_load_group_users_rejects_empty_selected_oj_users(self) -> None:
        """Verify empty user lists for the selected OJ are rejected."""
        group_file = Path("usergroup") / "empty.json"
        group_file.write_text(
            json.dumps({"atcoder": [], "cf": ["tourist"]}),
            encoding="utf-8",
        )

        with self.assertRaises(TrackerError):
            load_group_users("empty", "atcoder")

    def test_validate_contest(self) -> None:
        """Verify each adapter normalizes valid contests and rejects invalid ones."""
        atcoder = AtCoderAdapter()
        cf = CodeforcesAdapter()

        self.assertEqual(atcoder.validate_contest("abc403"), "abc403")
        self.assertEqual(cf.validate_contest("2065"), 2065)
        with self.assertRaises(TrackerError):
            cf.validate_contest("abc403")

    def test_expand_contest_token_supports_single_and_range_inputs(self) -> None:
        """Verify both adapters expand single contest IDs and inclusive ranges."""
        atcoder = AtCoderAdapter()
        cf = CodeforcesAdapter()

        self.assertEqual(atcoder.expand_contest_token("abc403"), ["abc403"])
        self.assertEqual(atcoder.expand_contest_token("abc403-abc405"), ["abc403", "abc404", "abc405"])
        self.assertEqual(cf.expand_contest_token("2065"), [2065])
        self.assertEqual(cf.expand_contest_token("2065-2067"), [2065, 2066, 2067])

    def test_expand_contest_token_rejects_invalid_cf_ranges(self) -> None:
        """Verify Codeforces rejects malformed or reversed contest ranges."""
        cf = CodeforcesAdapter()

        with self.assertRaises(TrackerError):
            cf.expand_contest_token("abc403-abc405")
        with self.assertRaises(TrackerError):
            cf.expand_contest_token("2067-2065")
        with self.assertRaises(TrackerError):
            cf.expand_contest_token("2065-")

    def test_expand_contest_token_rejects_invalid_atcoder_ranges(self) -> None:
        """Verify AtCoder rejects malformed, cross-prefix, or reversed ranges."""
        atcoder = AtCoderAdapter()

        with self.assertRaises(TrackerError):
            atcoder.expand_contest_token("abc300-arc305")
        with self.assertRaises(TrackerError):
            atcoder.expand_contest_token("abc405-abc403")
        with self.assertRaises(TrackerError):
            atcoder.expand_contest_token("abc300-305")

    def test_cache_has_done_contest_for_both_oj(self) -> None:
        """Verify contest matching works for both AtCoder and Codeforces submissions."""
        atcoder = AtCoderAdapter()
        cf = CodeforcesAdapter()

        atcoder_submissions = [
            {"id": 1, "contest_id": "AbC100"},
            {"id": 2, "contest_id": "abc200"},
        ]
        cf_submissions = [
            {"id": 3, "contestId": 2065},
            {"id": 4, "contestId": 1000},
        ]

        self.assertTrue(tracker_service.cache_has_done_contest(atcoder, atcoder_submissions, "abc100"))
        self.assertFalse(
            tracker_service.cache_has_done_contest(atcoder, atcoder_submissions, "abc300")
        )
        self.assertTrue(tracker_service.cache_has_done_contest(cf, cf_submissions, 2065))
        self.assertFalse(tracker_service.cache_has_done_contest(cf, cf_submissions, 2066))

    def test_parse_args_accepts_multiple_contests(self) -> None:
        """Verify argparse collects multiple contest values from a single -c option."""
        args = parse_args(["--oj", "atcoder", "-c", "abc403", "abc404", "-g", "example"])

        self.assertEqual(args.contest, ["abc403", "abc404"])


class CliOutputColorTest(unittest.TestCase):
    """Verify colored CLI output and multi-contest orchestration behavior."""

    def test_run_expands_ranges_in_input_order_and_updates_cache_once_per_user(self) -> None:
        """Verify CLI rendering preserves the established colors for emitted events."""
        fake_events = [
            CheckEvent(kind="checking_user", message="checking user alice ..."),
            CheckEvent(kind="checking_user", message="checking user bob ..."),
            CheckEvent(kind="contest_miss", message="no users have done abc402"),
            CheckEvent(kind="contest_hit", message="alice done abc403"),
            CheckEvent(kind="contest_hit", message="bob done abc404"),
        ]

        def fake_run_check(oj, group, contest_tokens, refresh_cache, *, reporter=None):
            self.assertEqual(oj, "atcoder")
            self.assertEqual(group, "example")
            self.assertEqual(contest_tokens, ["abc402", "abc403-abc404"])
            self.assertFalse(refresh_cache)
            for event in fake_events:
                reporter(event)
            return None

        stdout = io.StringIO()
        with (
            patch("src.cli.run_check", side_effect=fake_run_check),
            redirect_stdout(stdout),
        ):
            exit_code = run(["--oj", "atcoder", "-c", "abc402", "abc403-abc404", "-g", "example"])

        self.assertEqual(exit_code, 0)
        lines = stdout.getvalue().splitlines()
        self.assertEqual(lines[0], f"{ANSI_YELLOW}checking user alice ...{ANSI_RESET}")
        self.assertEqual(lines[1], f"{ANSI_YELLOW}checking user bob ...{ANSI_RESET}")
        self.assertEqual(lines[2], f"{ANSI_GREEN}no users have done abc402{ANSI_RESET}")
        self.assertEqual(lines[3], f"{ANSI_RED}alice done abc403{ANSI_RESET}")
        self.assertEqual(lines[4], f"{ANSI_RED}bob done abc404{ANSI_RESET}")

    def test_run_colors_no_hit_result_in_green_for_each_expanded_contest(self) -> None:
        """Verify the green no-hit color is preserved for each emitted miss event."""
        fake_events = [
            CheckEvent(kind="contest_miss", message="no users have done 2065"),
            CheckEvent(kind="contest_miss", message="no users have done 2066"),
        ]

        def fake_run_check(oj, group, contest_tokens, refresh_cache, *, reporter=None):
            self.assertEqual(oj, "cf")
            self.assertEqual(group, "example")
            self.assertEqual(contest_tokens, ["2065-2066"])
            self.assertFalse(refresh_cache)
            for event in fake_events:
                reporter(event)
            return None

        stdout = io.StringIO()
        with (
            patch("src.cli.run_check", side_effect=fake_run_check),
            redirect_stdout(stdout),
        ):
            exit_code = run(["--oj", "cf", "-c", "2065-2066", "-g", "example"])

        self.assertEqual(exit_code, 0)
        lines = stdout.getvalue().splitlines()
        self.assertEqual(lines[-2], f"{ANSI_GREEN}no users have done 2065{ANSI_RESET}")
        self.assertEqual(lines[-1], f"{ANSI_GREEN}no users have done 2066{ANSI_RESET}")

    def test_run_colors_warning_result_in_yellow(self) -> None:
        """Verify warning events use the warning color in CLI output."""
        fake_events = [
            CheckEvent(kind="contest_miss", message="no users have done 2065"),
            CheckEvent(
                kind="contest_warning",
                message="warning: tourist may have done 2065 via same-round contest 2066",
            ),
        ]

        def fake_run_check(oj, group, contest_tokens, refresh_cache, *, reporter=None):
            self.assertEqual(oj, "cf")
            self.assertEqual(group, "example")
            self.assertEqual(contest_tokens, ["2065"])
            self.assertFalse(refresh_cache)
            for event in fake_events:
                reporter(event)
            return None

        stdout = io.StringIO()
        with (
            patch("src.cli.run_check", side_effect=fake_run_check),
            redirect_stdout(stdout),
        ):
            exit_code = run(["--oj", "cf", "-c", "2065", "-g", "example"])

        self.assertEqual(exit_code, 0)
        lines = stdout.getvalue().splitlines()
        self.assertEqual(lines[0], f"{ANSI_GREEN}no users have done 2065{ANSI_RESET}")
        self.assertEqual(
            lines[1],
            f"{ANSI_YELLOW}warning: tourist may have done 2065 via same-round contest 2066{ANSI_RESET}",
        )

    def test_run_colors_catalog_update_in_yellow(self) -> None:
        """Verify contest-catalog refresh events use the yellow status color."""
        fake_events = [
            CheckEvent(
                kind="updating_contest_catalog",
                message="updating contest catalog for cf ...",
            ),
        ]

        def fake_run_check(oj, group, contest_tokens, refresh_cache, *, reporter=None):
            self.assertEqual(oj, "cf")
            self.assertEqual(group, "example")
            self.assertEqual(contest_tokens, ["2065"])
            self.assertFalse(refresh_cache)
            for event in fake_events:
                reporter(event)
            return None

        stdout = io.StringIO()
        with (
            patch("src.cli.run_check", side_effect=fake_run_check),
            redirect_stdout(stdout),
        ):
            exit_code = run(["--oj", "cf", "-c", "2065", "-g", "example"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            stdout.getvalue().splitlines(),
            [f"{ANSI_YELLOW}updating contest catalog for cf ...{ANSI_RESET}"],
        )

    def test_run_colors_catalog_warning_in_yellow(self) -> None:
        """Verify contest-catalog warnings use the yellow status color."""
        fake_events = [
            CheckEvent(
                kind="contest_catalog_warning",
                message="warning: failed to refresh contest catalog for cf, using cached catalog: boom",
            ),
        ]

        def fake_run_check(oj, group, contest_tokens, refresh_cache, *, reporter=None):
            self.assertEqual(oj, "cf")
            self.assertEqual(group, "example")
            self.assertEqual(contest_tokens, ["2065"])
            self.assertFalse(refresh_cache)
            for event in fake_events:
                reporter(event)
            return None

        stdout = io.StringIO()
        with (
            patch("src.cli.run_check", side_effect=fake_run_check),
            redirect_stdout(stdout),
        ):
            exit_code = run(["--oj", "cf", "-c", "2065", "-g", "example"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            stdout.getvalue().splitlines(),
            [
                (
                    f"{ANSI_YELLOW}warning: failed to refresh contest catalog for cf, "
                    f"using cached catalog: boom{ANSI_RESET}"
                )
            ],
        )

    def test_run_rejects_non_numeric_cf_contest_in_multi_contest_input(self) -> None:
        """Verify Codeforces contest input rejects any non-numeric token or range."""
        with self.assertRaises(TrackerError):
            run_check_payload = {}

            def fake_run_check(oj, group, contest_tokens, refresh_cache, *, reporter=None):
                del group
                del refresh_cache
                del reporter
                run_check_payload["oj"] = oj
                run_check_payload["contest_tokens"] = contest_tokens
                raise TrackerError("for --oj cf, --contest must be a pure numeric contestId")

            with patch("src.cli.run_check", side_effect=fake_run_check):
                run(["--oj", "cf", "-c", "2065", "abc403-abc405", "-g", "example"])

        self.assertEqual(run_check_payload["oj"], "cf")
        self.assertEqual(run_check_payload["contest_tokens"], ["2065", "abc403-abc405"])

    def test_main_colors_tracker_error_in_red_stderr(self) -> None:
        """Verify CLI domain errors are rendered to stderr using the error color."""
        stderr = io.StringIO()
        with patch("src.cli.run", side_effect=TrackerError("boom")), redirect_stderr(stderr):
            exit_code = main()

        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr.getvalue(), f"{ANSI_RED}error: boom{ANSI_RESET}\n")


if __name__ == "__main__":
    unittest.main()
