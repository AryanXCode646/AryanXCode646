"""Unit tests for scripts/update_profile.py."""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import scripts.update_profile as up


def _mock_http_response(payload: object, headers: dict[str, str] | None = None) -> MagicMock:
    encoded = json.dumps(payload).encode("utf-8")
    resp = MagicMock()
    resp.read.return_value = encoded
    resp.headers = headers or {}
    ctx = MagicMock()
    ctx.__enter__.return_value = resp
    ctx.__exit__.return_value = False
    return ctx


class TestResolveUsername(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_profile = os.environ.pop("PROFILE_USERNAME", None)
        self._orig_owner = os.environ.pop("GITHUB_REPOSITORY_OWNER", None)

    def tearDown(self) -> None:
        os.environ.pop("PROFILE_USERNAME", None)
        os.environ.pop("GITHUB_REPOSITORY_OWNER", None)
        if self._orig_profile is not None:
            os.environ["PROFILE_USERNAME"] = self._orig_profile
        if self._orig_owner is not None:
            os.environ["GITHUB_REPOSITORY_OWNER"] = self._orig_owner

    def test_default_username(self) -> None:
        self.assertEqual(up.resolve_username(), "AryanXCode646")

    def test_precedence_profile_over_owner(self) -> None:
        os.environ["PROFILE_USERNAME"] = "custom_user"
        os.environ["GITHUB_REPOSITORY_OWNER"] = "owner_user"
        self.assertEqual(up.resolve_username(), "custom_user")

    def test_owner_fallback_when_profile_empty(self) -> None:
        os.environ["PROFILE_USERNAME"] = "   "
        os.environ["GITHUB_REPOSITORY_OWNER"] = "owner_user"
        self.assertEqual(up.resolve_username(), "owner_user")


class TestGitHubApi(unittest.TestCase):
    @patch("scripts.update_profile.urlopen")
    def test_get_json_success(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_http_response({"login": "AryanXCode646"})
        result = up.get_json("/users/AryanXCode646")
        self.assertEqual(result, {"login": "AryanXCode646"})
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.full_url, f"{up.API}/users/AryanXCode646")
        self.assertEqual(mock_urlopen.call_args[1]["timeout"], up.DEFAULT_TIMEOUT)

    @patch("scripts.update_profile.urlopen")
    def test_get_json_http_error(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = HTTPError(
            url="https://api.github.com/users/invalid",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=io.BytesIO(b""),
        )
        with self.assertRaises(RuntimeError) as ctx:
            up.get_json("/users/invalid")
        self.assertIn("/users/invalid", str(ctx.exception))

    @patch("scripts.update_profile.urlopen")
    def test_get_json_rate_limit_error(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = HTTPError(
            url="https://api.github.com/users/AryanXCode646",
            code=403,
            msg="Forbidden",
            hdrs={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1700000000"},
            fp=io.BytesIO(b""),
        )
        with self.assertRaises(RuntimeError) as ctx:
            up.get_json("/users/AryanXCode646")
        self.assertIn("rate limit", str(ctx.exception).lower())

    @patch("scripts.update_profile.urlopen")
    def test_get_json_network_error(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = URLError("timed out")
        with self.assertRaises(RuntimeError) as ctx:
            up.get_json("/users/AryanXCode646")
        self.assertIn("network error", str(ctx.exception).lower())

    @patch("scripts.update_profile.urlopen")
    def test_fetch_all_repos_pagination_over_100(self, mock_urlopen: MagicMock) -> None:
        page1 = [{"name": f"repo-{i}", "fork": False, "archived": False} for i in range(100)]
        page2 = [{"name": f"repo-{i}", "fork": False, "archived": False} for i in range(100, 125)]
        mock_urlopen.side_effect = [
            _mock_http_response(
                page1,
                headers={"Link": '<https://api.github.com/users/AryanXCode646/repos?page=2>; rel="next"'},
            ),
            _mock_http_response(page2, headers={}),
        ]
        repos = up.fetch_all_repos("AryanXCode646")
        self.assertEqual(len(repos), 125)
        self.assertEqual(mock_urlopen.call_count, 2)

    @patch("scripts.update_profile.urlopen")
    def test_fetch_all_repos_empty(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_http_response([])
        repos = up.fetch_all_repos("AryanXCode646")
        self.assertEqual(repos, [])


class TestMarkersAndFormatting(unittest.TestCase):
    def test_update_marker_success(self) -> None:
        text = "before\n<!-- START -->\nold\n<!-- END -->\nafter"
        result = up.update_marker(text, "<!-- START -->", "<!-- END -->", "new \\1 content")
        self.assertIn("new \\1 content", result)
        self.assertNotIn("old", result)

    def test_update_marker_missing(self) -> None:
        with self.assertRaises(RuntimeError):
            up.update_marker("no markers here", "<!-- START -->", "<!-- END -->", "new")

    def test_update_marker_duplicate(self) -> None:
        text = "<!-- START -->a<!-- END -->\n<!-- START -->b<!-- END -->"
        with self.assertRaises(RuntimeError) as ctx:
            up.update_marker(text, "<!-- START -->", "<!-- END -->", "new")
        self.assertIn("Duplicate", str(ctx.exception))

    def test_build_profile_filters_forks_and_archived(self) -> None:
        profile = {"public_repos": 4, "followers": 10, "following": 5}
        repos = [
            {
                "name": "active-1",
                "fork": False,
                "archived": False,
                "stargazers_count": 7,
                "language": "Python",
                "pushed_at": "2026-11-20T00:00:00Z",
                "html_url": "https://github.com/AryanXCode646/active-1",
            },
            {
                "name": "forked-repo",
                "fork": True,
                "archived": False,
                "stargazers_count": 99,
                "language": "Go",
                "pushed_at": "2026-11-25T00:00:00Z",
                "html_url": "https://github.com/AryanXCode646/forked-repo",
            },
            {
                "name": "archived-repo",
                "fork": False,
                "archived": True,
                "stargazers_count": 50,
                "language": "C++",
                "pushed_at": "2026-11-24T00:00:00Z",
                "html_url": "https://github.com/AryanXCode646/archived-repo",
            },
        ]
        output = up.build_profile(profile, repos, "2026-11-28 00:00 UTC")
        self.assertIn("`4`", output)
        self.assertIn("`1`", output)
        self.assertIn("★ 7", output)
        self.assertNotIn("99", output)
        self.assertNotIn("50", output)
        self.assertIn("`Python` (1)", output)
        self.assertNotIn("`Go`", output)
        self.assertIn("[`active-1`]", output)

    def test_build_profile_empty_repos(self) -> None:
        profile = {"public_repos": 0, "followers": 0, "following": 0}
        output = up.build_profile(profile, [], "2026-11-28 00:00 UTC")
        self.assertIn("`0`", output)
        self.assertIn("★ 0", output)
        self.assertIn("| — |", output)

    def test_build_activity_escapes_table_chars_and_unicode(self) -> None:
        repos = [
            {
                "name": "pipe|repo",
                "fork": False,
                "archived": False,
                "description": "Fast | reliable <ML> & café pipeline\nline2",
                "language": "Python",
                "stargazers_count": 3,
                "pushed_at": "2026-11-27T10:00:00Z",
                "html_url": "https://github.com/AryanXCode646/pipe-repo",
            }
        ]
        output = up.build_activity(repos, "2026-11-28 00:00 UTC")
        self.assertIn("pipe\\|repo", output)
        self.assertIn("Fast \\| reliable &lt;ML&gt; &amp; café pipeline line2", output)
        self.assertIn("`2026-11-27`", output)

    def test_build_activity_empty(self) -> None:
        output = up.build_activity([], "2026-11-28 00:00 UTC")
        self.assertIn("No active non-fork repositories found.", output)

    def test_build_svg_valid_xml_and_unicode(self) -> None:
        profile = {"public_repos": 12, "followers": 44, "following": 112}
        repos = [
            {"name": "r1", "fork": False, "archived": False, "stargazers_count": 8},
            {"name": "r2", "fork": True, "archived": False, "stargazers_count": 999},
        ]
        svg = up.build_svg(profile, repos, "2026-11-28 00:00 UTC")
        root = ET.fromstring(svg)
        self.assertTrue(root.tag.endswith("svg"))
        self.assertIn("PUBLIC REPOS", svg)
        self.assertIn("OWNED STARS", svg)
        self.assertIn("★ 8", svg)
        self.assertNotIn("999", svg)

    def test_main_updates_readme_and_svg_safely(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            readme_path = root / "README.md"
            svg_path = root / "assets" / "profile-metrics.svg"
            readme_path.write_text(
                "# Header\n\n<!-- PROFILE:START -->\nold\n<!-- PROFILE:END -->\n\n"
                "## Keep Me\n\n<!-- ACTIVITY:START -->\nold\n<!-- ACTIVITY:END -->\n",
                encoding="utf-8",
            )
            profile = {"public_repos": 5, "followers": 10, "following": 2}
            repos = [
                {
                    "name": "demo",
                    "fork": False,
                    "archived": False,
                    "description": "Demo repo",
                    "language": "Python",
                    "stargazers_count": 4,
                    "pushed_at": "2026-11-28T00:00:00Z",
                    "html_url": "https://github.com/AryanXCode646/demo",
                }
            ]
            with (
                patch.object(up, "README", readme_path),
                patch.object(up, "SVG", svg_path),
                patch("scripts.update_profile.get_json", return_value=profile),
                patch("scripts.update_profile.fetch_all_repos", return_value=repos),
            ):
                up.main()

            updated_readme = readme_path.read_text(encoding="utf-8")
            self.assertIn("# Header", updated_readme)
            self.assertIn("## Keep Me", updated_readme)
            self.assertIn("[`demo`](https://github.com/AryanXCode646/demo)", updated_readme)
            svg_content = svg_path.read_text(encoding="utf-8")
            ET.fromstring(svg_content)
            self.assertIn("★ 4", svg_content)

    def test_atomic_write_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "nested" / "out.txt"
            up.atomic_write_text(target, "hello café\n")
            self.assertEqual(target.read_text(encoding="utf-8"), "hello café\n")
            # No leftover .tmp files
            leftovers = [p for p in target.parent.iterdir() if p.name != "out.txt"]
            self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
