import unittest
from pathlib import Path


def read_script(name: str) -> str:
    return Path(name).read_text(encoding="utf-8")


class TestBatchScripts(unittest.TestCase):
    def test_run_script_starts_local_server_and_cleans_up_only_when_it_started_it(self):
        script = read_script("run.bat")

        self.assertIn("curl -s http://127.0.0.1:8080/health", script)
        self.assertIn('start "" /min "%SCRIPT_DIR%start_server.bat"', script)
        self.assertIn("set SERVER_WAS_RUNNING=1", script)
        self.assertIn("set SERVER_WAS_RUNNING=0", script)
        self.assertIn("if %SERVER_WAS_RUNNING% equ 0", script)
        self.assertIn("taskkill /PID %SERVER_PID% /F", script)

    def test_start_server_binds_to_loopback_after_model_verification(self):
        script = read_script("start_server.bat")

        self.assertIn('python "%SCRIPT_DIR%verify_model.py"', script)
        self.assertIn("--host 127.0.0.1", script)
        self.assertIn("--port 8080", script)
        self.assertNotIn("--host 0.0.0.0", script)

    def test_process_script_requires_running_local_server_before_processing(self):
        script = read_script("process.bat")

        self.assertIn('if exist "%SCRIPT_DIR%venv\\Scripts\\activate.bat"', script)
        self.assertIn('if not exist "%INPUT_DIR%"', script)
        self.assertIn("curl -s http://127.0.0.1:8080/health", script)
        self.assertIn('python "%SCRIPT_DIR%process_pdfs.py"', script)
        self.assertIn("--workers 1", script)

    def test_install_script_uses_venv_requirements_and_creates_work_dirs(self):
        script = read_script("install.bat")

        self.assertIn('python -m venv "%SCRIPT_DIR%venv"', script)
        self.assertIn('call "%SCRIPT_DIR%venv\\Scripts\\activate.bat"', script)
        self.assertIn('python -m pip install -r "%SCRIPT_DIR%requirements.txt"', script)
        self.assertIn('python "%SCRIPT_DIR%setup_llm.py" --accept-model-download', script)
        self.assertIn('if not exist "%SCRIPT_DIR%input" mkdir "%SCRIPT_DIR%input"', script)
        self.assertIn('if not exist "%SCRIPT_DIR%output" mkdir "%SCRIPT_DIR%output"', script)


if __name__ == "__main__":
    unittest.main()
