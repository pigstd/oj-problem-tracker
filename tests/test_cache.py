import datetime
import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "atcoder-problem-tracker.py"
SPEC = importlib.util.spec_from_file_location("tracker", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("failed to load tracker module")
tracker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tracker)


def _iso_utc_hours_ago(hours: int) -> str:
    timestamp = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
    return timestamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _cache_payload(user_id: str, last_updated_at: str, next_from_second: int, submissions: list[dict]):
    return {
        "version": tracker.CACHE_VERSION,
        "user_id": user_id,
        "last_updated_at": last_updated_at,
        "next_from_second": next_from_second,
        "submissions": submissions,
    }


class CacheBehaviorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original_cache_dir = tracker.CACHE_DIR
        self.original_fetch = tracker.fetch_submissions_with_retry
        tracker.CACHE_DIR = Path(self.tmpdir.name) / "cache/users"
        tracker.ensure_cache_dir_exists()

    def tearDown(self) -> None:
        tracker.CACHE_DIR = self.original_cache_dir
        tracker.fetch_submissions_with_retry = self.original_fetch
        self.tmpdir.cleanup()

    def test_create_cache_for_new_user(self) -> None:
        def fake_fetch(user_id: str, from_second: int):
            self.assertEqual(user_id, "alice")
            if from_second == 0:
                return [{"id": 1, "epoch_second": 100, "contest_id": "abc100"}]
            if from_second == 101:
                return []
            self.fail(f"unexpected from_second={from_second}")

        tracker.fetch_submissions_with_retry = fake_fetch
        cache = tracker.update_user_cache("alice", refresh_cache=False)

        self.assertEqual(cache["next_from_second"], 101)
        self.assertEqual(len(cache["submissions"]), 1)
        self.assertTrue(tracker.get_cache_file_path("alice").exists())

    def test_skip_update_within_interval(self) -> None:
        payload = _cache_payload(
            user_id="bob",
            last_updated_at=_iso_utc_hours_ago(1),
            next_from_second=42,
            submissions=[{"id": 11, "epoch_second": 41, "contest_id": "abc001"}],
        )
        tracker.write_user_cache("bob", payload)

        called = {"value": False}

        def fake_fetch(_: str, __: int):
            called["value"] = True
            return []

        tracker.fetch_submissions_with_retry = fake_fetch
        cache = tracker.update_user_cache("bob", refresh_cache=False)

        self.assertFalse(called["value"])
        self.assertEqual(cache["next_from_second"], 42)
        self.assertEqual(len(cache["submissions"]), 1)

    def test_incremental_update_and_dedup(self) -> None:
        payload = _cache_payload(
            user_id="carol",
            last_updated_at=_iso_utc_hours_ago(48),
            next_from_second=10,
            submissions=[{"id": 1, "epoch_second": 9, "contest_id": "abc001"}],
        )
        tracker.write_user_cache("carol", payload)

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

        tracker.fetch_submissions_with_retry = fake_fetch
        cache = tracker.update_user_cache("carol", refresh_cache=False)

        self.assertEqual(cache["next_from_second"], 13)
        self.assertEqual([s["id"] for s in cache["submissions"]], [1, 2])

    def test_refresh_cache_rebuilds_from_zero(self) -> None:
        payload = _cache_payload(
            user_id="dave",
            last_updated_at=_iso_utc_hours_ago(1),
            next_from_second=20,
            submissions=[{"id": 9, "epoch_second": 19, "contest_id": "abc001"}],
        )
        tracker.write_user_cache("dave", payload)

        def fake_fetch(user_id: str, from_second: int):
            self.assertEqual(user_id, "dave")
            if from_second == 0:
                return [{"id": 101, "epoch_second": 7, "contest_id": "abc777"}]
            if from_second == 8:
                return []
            self.fail(f"unexpected from_second={from_second}")

        tracker.fetch_submissions_with_retry = fake_fetch
        cache = tracker.update_user_cache("dave", refresh_cache=True)

        self.assertEqual(cache["next_from_second"], 8)
        self.assertEqual([s["id"] for s in cache["submissions"]], [101])

    def test_cache_contest_matching_is_case_insensitive(self) -> None:
        submissions = [
            {"id": 1, "contest_id": "AbC100"},
            {"id": 2, "contest_id": "abc200"},
        ]
        self.assertTrue(tracker.cache_has_done_contest(submissions, "abc100"))
        self.assertFalse(tracker.cache_has_done_contest(submissions, "abc300"))


if __name__ == "__main__":
    unittest.main()
