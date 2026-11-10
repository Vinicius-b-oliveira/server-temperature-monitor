import subprocess
import sys

from app import config, database
from conftest import telemetry
from reset_db import reset

SERVER_DIR = config.SERVER_DIR


def test_reset_moves_db_to_backup(tmp_path):
    db_path = tmp_path / "monitor.db"
    database.init_db(db_path)
    database.insert_reading(db_path, telemetry())

    backup = reset(db_path)

    assert backup.parent == tmp_path / "backup"
    assert backup.name.startswith("monitor-")
    assert database.latest_reading(backup) is not None
    assert database.latest_reading(db_path) is None


def test_reset_without_db_creates_it(tmp_path):
    db_path = tmp_path / "monitor.db"
    assert reset(db_path) is None
    assert db_path.exists()
    assert not (tmp_path / "backup").exists()


def test_cli_with_yes_flag(tmp_path):
    db_path = tmp_path / "monitor.db"
    database.init_db(db_path)
    result = subprocess.run(
        [sys.executable, "reset_db.py", "--yes"],
        cwd=SERVER_DIR, env={"DB_PATH": str(db_path)}, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Backup em:" in result.stdout
    assert len(list((tmp_path / "backup").glob("monitor-*.db"))) == 1


def test_cli_without_confirmation_changes_nothing(tmp_path):
    db_path = tmp_path / "monitor.db"
    database.init_db(db_path)
    result = subprocess.run(
        [sys.executable, "reset_db.py"],
        cwd=SERVER_DIR, env={"DB_PATH": str(db_path)}, input="n\n", capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Nada foi alterado." in result.stdout
    assert not (tmp_path / "backup").exists()
