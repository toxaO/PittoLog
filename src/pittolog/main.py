from __future__ import annotations

import shutil
import sys
from pathlib import Path

from pittolog.app import run_app


def main() -> int:
    app_dir = application_dir()
    db_path = app_dir / "data" / "pittolog.sqlite"
    migrate_legacy_databases(
        [
            app_dir / "pittolog.sqlite",
            app_dir / "data" / "bbmanager.sqlite",
            app_dir / "bbmanager.sqlite",
        ],
        db_path,
    )
    return run_app(db_path)


def application_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def migrate_legacy_database(legacy_path: Path, db_path: Path) -> None:
    if db_path.exists() or not legacy_path.exists():
        return
    db_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(legacy_path, db_path)


def migrate_legacy_databases(legacy_paths: list[Path], db_path: Path) -> None:
    for legacy_path in legacy_paths:
        migrate_legacy_database(legacy_path, db_path)
        if db_path.exists():
            return


if __name__ == "__main__":
    raise SystemExit(main())
