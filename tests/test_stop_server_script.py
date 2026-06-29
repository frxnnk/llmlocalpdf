import unittest
from pathlib import Path


class TestStopServerScript(unittest.TestCase):
    def test_pid_branch_uses_delayed_expansion(self):
        script = Path("stop_server.bat").read_text(encoding="utf-8")

        self.assertIn("EnableDelayedExpansion", script)
        self.assertIn("!SERVER_PID!", script)
        self.assertIn("!errorlevel!", script)
        self.assertNotIn("(PID:", script)


if __name__ == "__main__":
    unittest.main()
