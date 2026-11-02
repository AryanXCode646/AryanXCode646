#!/usr/bin/env python3
"""Unit tests for update_profile script"""
import os
import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import scripts.update_profile as up

class TestUpdateProfile(unittest.TestCase):
    def setUp(self):
        # Clean environment variables
        os.environ.pop('PROFILE_USERNAME', None)
        os.environ.pop('GITHUB_REPOSITORY_OWNER', None)

    def test_username_fallback(self):
        # Default username
        self.assertEqual(up.USERNAME, "AryanSaxena20")
        # PROFILE_USERNAME overrides
        os.environ['PROFILE_USERNAME'] = 'testuser'
        self.assertEqual(up.USERNAME, 'testuser')
        # GITHUB_REPOSITORY_OWNER when PROFILE_USERNAME absent
        os.environ.pop('PROFILE_USERNAME')
        os.environ['GITHUB_REPOSITORY_OWNER'] = 'owneruser'
        self.assertEqual(up.USERNAME, 'owneruser')

    @patch('scripts.update_profile.urlopen')
    def test_get_json_http_error(self, mock_urlopen):
        # Simulate HTTPError (e.g., 404)
        mock_urlopen.side_effect = HTTPError(url='https://api.github.com/users/invalid', code=404, msg='Not Found', hdrs=None, fp=None)
        os.environ['PROFILE_USERNAME'] = 'invalid'
        with self.assertRaises(RuntimeError) as ctx:
            up.get_json(f"/users/invalid")
        self.assertIn('/users/invalid', str(ctx.exception))

    @patch('scripts.update_profile.urlopen')
    def test_get_json_success(self, mock_urlopen):
        # Mock successful JSON response
        mock_response = MagicMock()
        mock_response.__enter__.return_value = MagicMock(read=lambda: b'{"key": "value"}')
        mock_urlopen.side_effect = None
        mock_urlopen.return_value = mock_response
        os.environ['PROFILE_USERNAME'] = 'testuser'
        result = up.get_json(f"/users/testuser")
        self.assertEqual(result, {"key": "value"})
        expected_url = f"{up.API}/users/testuser"
        mock_urlopen.assert_called_once()
        args, _ = mock_urlopen.call_args
        self.assertIn(expected_url, args[0].full_url)

    def test_update_marker_success(self):
        text = "before\n<!-- START -->\nold\n<!-- END -->\nafter"
        new = "new content"
        result = up.update_marker(text, "<!-- START -->", "<!-- END -->", new)
        self.assertIn(new, result)
        self.assertNotIn("old", result)

    def test_update_marker_missing(self):
        text = "no markers here"
        with self.assertRaises(RuntimeError):
            up.update_marker(text, "<!-- START -->", "<!-- END -->", "new")

    def test_build_profile_basic(self):
        profile = {'public_repos': 2, 'followers': 5, 'following': 3, 'public_gists': 1}
        repos = [
            {'name': 'repo1', 'fork': False, 'archived': False, 'stargazers_count': 10, 'language': 'Python', 'html_url': 'https://github.com/AryanSaxena20/repo1'},
            {'name': 'repo2', 'fork': False, 'archived': False, 'stargazers_count': 5, 'language': 'JavaScript', 'html_url': 'https://github.com/AryanSaxena20/repo2'}
        ]
        now = '2026-11-02 00:00 UTC'
        output = up.build_profile(profile, repos, now)
        self.assertIn('Public Repositories', output)
        self.assertIn('2', output)
        self.assertIn('★ 15', output)  # total stars
        self.assertIn('`Python` (1)', output)
        self.assertIn('`JavaScript` (1)', output)
        self.assertIn('2026-11-02 00:00 UTC', output)

    def test_build_activity_basic(self):
        repos = [
            {'name': 'repo1', 'description': 'Desc', 'language': 'Python', 'stargazers_count': 2, 'pushed_at': '2026-11-01T12:00:00Z', 'html_url': 'https://github.com/AryanSaxena20/repo1'},
            {'name': 'repo2', 'description': None, 'language': None, 'stargazers_count': 3, 'pushed_at': '2026-11-02T12:00:00Z', 'html_url': 'https://github.com/AryanSaxena20/repo2'}
        ]
        now = '2026-11-02 00:00 UTC'
        output = up.build_activity(repos, now)
        self.assertIn('repo1', output)
        self.assertIn('repo2', output)
        self.assertIn('Python', output)
        self.assertIn('★ 2', output)
        self.assertIn('2026-11-01', output)
        self.assertIn('2026-11-02', output)
        self.assertIn('2026-11-02 00:00 UTC', output)

    def test_build_svg_valid(self):
        profile = {'public_repos': 1, 'followers': 2, 'following': 3, 'public_gists': 0}
        repos = []
        now = '2026-11-02 00:00 UTC'
        svg = up.build_svg(profile, repos, now)
        import xml.etree.ElementTree as ET
        try:
            ET.fromstring(svg)
        except ET.ParseError as e:
            self.fail(f'SVG not valid XML: {e}')
        self.assertIn('REPOSITORIES', svg)
        self.assertIn('1', svg)

if __name__ == '__main__':
    unittest.main()
