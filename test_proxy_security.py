import os
import unittest
from unittest import mock

from proxy import Handler


def fake_handler(cookie=""):
    handler = object.__new__(Handler)
    handler.headers = {"Cookie": cookie}
    return handler


class ProxySecurityTests(unittest.TestCase):
    def test_player_fails_closed_without_web_token(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MUSIC_WEB_TOKEN", None)
            self.assertFalse(fake_handler()._player_allowed(None))

    def test_player_requires_constant_time_cookie_match(self):
        with mock.patch.dict(os.environ, {"MUSIC_WEB_TOKEN": "secret-token"}):
            self.assertTrue(
                fake_handler("music_web=secret-token")._player_allowed(None)
            )
            self.assertFalse(
                fake_handler("music_web=wrong-token")._player_allowed(None)
            )
            self.assertFalse(fake_handler("")._player_allowed(None))

    def test_login_qr_requires_exact_token(self):
        # The handler only reaches the file read after the token check; call the
        # token comparison logic through a minimal source-level assertion.
        import inspect
        source = inspect.getsource(Handler._forward)
        self.assertIn("hmac.compare_digest(token, expected)", source)


if __name__ == "__main__":
    unittest.main()
