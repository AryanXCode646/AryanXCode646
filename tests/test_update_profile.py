#!/usr/bin/env python3
"""Unit tests for update_profile script"""
import os
import unittest
from unittest.mock import patch, MagicMock
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import scripts.update_profile as up

class TestUpdateProfile(unittest.TestCase):
    def setUp(self):
        # Clean env
        os.environ.pop('PROFILE_USERNAME', None)
        os.environ.pop('GITHUB_REPOSITORY_OWNER', None)
        # Reset USERNAME to default fallback
        up.USERNAME = os.getenv('PROFILE_USERNAME') or os.getenv('GITHUB_REPOSITORY_OWNER') or "AryanSaxena20"

    def test_username_fallback(self):
        # Default
        self.assertEqual(up.USERNAME, "AryanSaxena20")
        # PROFILE_USERNAME
        os.environ['PROFILE_USERNAME'] = 'testuser'
        up.USERNAME = os.getenv('PROFILE_USERNAME') or os.getenv('GITHUB_REPOSITORY_OWNER') or "AryanSaxena20"
        self.assertEqual(up.USERNAME, 'testuser')
        # GITHUB_REPOSITORY_OWNER when PROFILE_USERNAME absent
        os.environ.pop('PROFILE_USERNAME')
        os.environ['GITHUB_REPOSITORY_OWNER'] = 'owneruser'
        up.USERNAME = os.getenv('PROFILE_USERNAME') or os.getenv('GITHUB_REPOSITORY_OWNER') or "AryanSaxena20"
        self.assertEqual(up.USERNAME, 'owneruser')

    @patch('scripts.update_profile.urlopen')
    def test_get_json_success(self, mock_urlopen):
        # Mock response
        mock_response = MagicMock()
        mock_response.__enter__.return_value = MagicMock(read=lambda: b'{"key": "value"}')
        mock_urlopen.return_value = mock_response
        # Ensure USERNAME set
        os.environ['PROFILE_USERNAME'] = 'testuser'
        up.USERNAME = os.getenv('PROFILE_USERNAME') or os.getenv('GITHUB_REPOSITORY_OWNER') or "AryanSaxena20"
        result = up.get_json(f"/users/{up.USERNAME}")
        self.assertEqual(result, {"key": "value"})
        expected_url = f"{up.API}/users/{up.USERNAME}"
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

if __name__ == '__main__':
    unittest.main()
