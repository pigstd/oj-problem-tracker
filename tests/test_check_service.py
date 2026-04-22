import unittest
from unittest.mock import patch

from src.core.checks import run_check


class StructuredCheckServiceTest(unittest.TestCase):
    """Verify the structured check service feeds both CLI and web use cases."""

    def test_run_check_returns_structured_results_and_events(self) -> None:
        """Verify one run returns ordered events, user summaries, and contest summaries."""

        class FakeAdapter:
            name = "atcoder"

            def expand_contest_token(self, token: str) -> list[str]:
                mapping = {
                    "abc402": ["abc402"],
                    "abc403-abc404": ["abc403", "abc404"],
                }
                return mapping[token]

            def submission_matches_contest(self, submission: dict, contest: str) -> bool:
                return submission.get("contest_id") == contest

        def fake_update_user_cache(adapter, user_id, refresh_cache, *, status_callback=None, emit_output=True):
            self.assertIsInstance(adapter, FakeAdapter)
            self.assertFalse(refresh_cache)
            self.assertFalse(emit_output)

            if user_id == "alice":
                status_callback("updating_cache", "updating cache for alice ...")
                return {"submissions": [{"contest_id": "abc403"}]}

            status_callback("cache_hit", "cache hit, skip update for bob")
            return {"submissions": [{"contest_id": "abc404"}]}

        emitted_events = []
        with (
            patch("src.core.checks.get_adapter", return_value=FakeAdapter()),
            patch("src.core.checks.load_group_users", return_value=["alice", "bob"]),
            patch("src.core.checks.cache.ensure_cache_dir_exists"),
            patch("src.core.checks.tracker.update_user_cache", side_effect=fake_update_user_cache),
        ):
            result = run_check(
                "atcoder",
                "example",
                ["abc402", "abc403-abc404"],
                False,
                reporter=emitted_events.append,
            )

        self.assertEqual(result.expanded_contests, ["abc402", "abc403", "abc404"])
        self.assertEqual(
            result.contest_summaries[0].matched_users,
            [],
        )
        self.assertEqual(result.contest_summaries[1].matched_users, ["alice"])
        self.assertEqual(result.contest_summaries[2].matched_users, ["bob"])
        self.assertEqual(
            [event.kind for event in emitted_events],
            [
                "checking_user",
                "updating_cache",
                "checking_user",
                "cache_hit",
                "contest_miss",
                "contest_hit",
                "contest_hit",
            ],
        )
        self.assertEqual(result.to_dict()["events"][0]["message"], "checking user alice ...")
