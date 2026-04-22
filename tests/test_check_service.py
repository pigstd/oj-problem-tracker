import unittest
from unittest.mock import patch

from src.core.checks import run_check
from src.oj.base import TargetContestSelection


class StructuredCheckServiceTest(unittest.TestCase):
    """Verify the structured check service feeds both CLI and web use cases."""

    def test_run_check_returns_structured_results_and_events(self) -> None:
        """Verify one run returns ordered events, user summaries, and contest summaries."""

        class FakeAdapter:
            name = "atcoder"

            def prepare_run(self, refresh_cache: bool, *, status_callback=None) -> None:
                self.refresh_cache = refresh_cache
                del status_callback

            def expand_contest_token(self, token: str) -> list[str]:
                mapping = {
                    "abc402": ["abc402"],
                    "abc403-abc404": ["abc403", "abc404"],
                }
                return mapping[token]

            def submission_matches_contest(self, submission: dict, contest: str) -> bool:
                return submission.get("contest_id") == contest

            def find_warning_matches(self, submissions: list[dict], contest: str) -> list[str]:
                del submissions
                del contest
                return []

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

    def test_run_check_accepts_inline_group_users_without_loading_group_files(self) -> None:
        """Verify inline group payloads bypass the legacy group-file loader."""

        class FakeAdapter:
            name = "atcoder"

            def prepare_run(self, refresh_cache: bool, *, status_callback=None) -> None:
                del refresh_cache
                del status_callback

            def expand_contest_token(self, token: str) -> list[str]:
                return [token]

            def submission_matches_contest(self, submission: dict, contest: str) -> bool:
                return submission.get("contest_id") == contest

            def find_warning_matches(self, submissions: list[dict], contest: str) -> list[str]:
                del submissions
                del contest
                return []

        def fake_update_user_cache(adapter, user_id, refresh_cache, *, status_callback=None, emit_output=True):
            del adapter
            del refresh_cache
            del status_callback
            del emit_output
            return {"submissions": [{"contest_id": "abc403"}]}

        with (
            patch("src.core.checks.get_adapter", return_value=FakeAdapter()),
            patch("src.core.checks.load_group_users") as load_group_users,
            patch("src.core.checks.cache.ensure_cache_dir_exists"),
            patch("src.core.checks.tracker.update_user_cache", side_effect=fake_update_user_cache),
        ):
            result = run_check(
                "atcoder",
                "local-demo",
                ["abc403"],
                False,
                group_users_by_oj={
                    "atcoder": ["alice"],
                    "cf": [],
                },
            )

        load_group_users.assert_not_called()
        self.assertEqual(result.group, "local-demo")
        self.assertEqual(result.users, ["alice"])
        self.assertEqual(result.contest_summaries[0].matched_users, ["alice"])

    def test_run_check_emits_warning_for_same_round_sibling_match(self) -> None:
        """Verify same-round sibling matches emit both miss and warning results."""

        class FakeAdapter:
            name = "cf"

            def prepare_run(self, refresh_cache: bool, *, status_callback=None) -> None:
                self.refresh_cache = refresh_cache
                del status_callback

            def expand_contest_token(self, token: str) -> list[int]:
                return [int(token)]

            def submission_matches_contest(self, submission: dict, contest: int) -> bool:
                return submission.get("contestId") == contest

            def find_warning_matches(self, submissions: list[dict], contest: int) -> list[int]:
                if any(submission.get("contestId") == 2066 for submission in submissions):
                    return [2066]
                return []

        def fake_update_user_cache(adapter, user_id, refresh_cache, *, status_callback=None, emit_output=True):
            self.assertIsInstance(adapter, FakeAdapter)
            self.assertFalse(refresh_cache)
            self.assertFalse(emit_output)
            status_callback("cache_hit", f"cache hit, skip update for {user_id}")
            return {"submissions": [{"contestId": 2066}]}

        emitted_events = []
        with (
            patch("src.core.checks.get_adapter", return_value=FakeAdapter()),
            patch("src.core.checks.load_group_users", return_value=["tourist"]),
            patch("src.core.checks.cache.ensure_cache_dir_exists"),
            patch("src.core.checks.tracker.update_user_cache", side_effect=fake_update_user_cache),
        ):
            result = run_check(
                "cf",
                "example",
                ["2065"],
                False,
                reporter=emitted_events.append,
            )

        self.assertEqual(result.contest_summaries[0].matched_users, [])
        self.assertEqual(result.contest_summaries[0].warnings[0].user_id, "tourist")
        self.assertEqual(result.contest_summaries[0].warnings[0].warning_contests, ["2066"])
        self.assertEqual(
            [event.kind for event in emitted_events],
            ["checking_user", "cache_hit", "contest_miss", "contest_warning"],
        )

    def test_run_check_emits_prepare_run_status_before_user_checks(self) -> None:
        """Verify adapter setup events are emitted before the first user cache check."""

        class FakeAdapter:
            name = "cf"

            def prepare_run(self, refresh_cache: bool, *, status_callback=None) -> None:
                self.refresh_cache = refresh_cache
                status_callback("updating_contest_catalog", "updating contest catalog for cf ...")

            def expand_contest_token(self, token: str) -> list[int]:
                return [int(token)]

            def submission_matches_contest(self, submission: dict, contest: int) -> bool:
                return submission.get("contestId") == contest

            def find_warning_matches(self, submissions: list[dict], contest: int) -> list[int]:
                del submissions
                del contest
                return []

        def fake_update_user_cache(adapter, user_id, refresh_cache, *, status_callback=None, emit_output=True):
            self.assertIsInstance(adapter, FakeAdapter)
            self.assertFalse(refresh_cache)
            self.assertFalse(emit_output)
            status_callback("cache_hit", f"cache hit, skip update for {user_id}")
            return {"submissions": []}

        emitted_events = []
        with (
            patch("src.core.checks.get_adapter", return_value=FakeAdapter()),
            patch("src.core.checks.load_group_users", return_value=["tourist"]),
            patch("src.core.checks.cache.ensure_cache_dir_exists"),
            patch("src.core.checks.tracker.update_user_cache", side_effect=fake_update_user_cache),
        ):
            run_check(
                "cf",
                "example",
                ["2065"],
                False,
                reporter=emitted_events.append,
            )

        self.assertEqual(
            [event.kind for event in emitted_events],
            ["updating_contest_catalog", "checking_user", "cache_hit", "contest_miss"],
        )

    def test_run_check_skips_filtered_contests_without_touching_user_cache_when_none_are_selected(self) -> None:
        """Verify fully skipped contest selections do not trigger user-cache refreshes."""

        class FakeAdapter:
            name = "cf"

            def prepare_run(self, refresh_cache: bool, *, status_callback=None) -> None:
                del refresh_cache
                del status_callback

            def expand_contest_token(self, token: str) -> list[int]:
                return [int(token)]

            def select_target_contests(self, contests: list[int], *, selected_contest_types=None):
                self.selected_contest_types = selected_contest_types
                return [
                    TargetContestSelection(
                        contest=contest,
                        status="skipped",
                        contest_type="div2",
                        skip_reason="contest type div2 is not in selected types div1",
                    )
                    for contest in contests
                ]

            def submission_matches_contest(self, submission: dict, contest: int) -> bool:
                del submission
                del contest
                return False

            def find_warning_matches(self, submissions: list[dict], contest: int) -> list[int]:
                del submissions
                del contest
                return []

        emitted_events = []
        with (
            patch("src.core.checks.get_adapter", return_value=FakeAdapter()),
            patch("src.core.checks.load_group_users", return_value=["tourist"]),
            patch("src.core.checks.cache.ensure_cache_dir_exists"),
            patch("src.core.checks.tracker.update_user_cache") as update_user_cache,
        ):
            result = run_check(
                "cf",
                "example",
                ["2065"],
                False,
                contest_types=["div1"],
                reporter=emitted_events.append,
            )

        update_user_cache.assert_not_called()
        self.assertEqual(result.contest_summaries[0].status, "skipped")
        self.assertEqual(result.contest_summaries[0].contest_type, "div2")
        self.assertEqual(
            result.contest_summaries[0].skip_reason,
            "contest type div2 is not in selected types div1",
        )
        self.assertEqual([event.kind for event in emitted_events], ["contest_skipped"])
