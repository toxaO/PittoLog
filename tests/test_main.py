from __future__ import annotations

from pittolog.main import migrate_legacy_database, migrate_legacy_databases


def test_migrate_legacy_database_copies_root_database_to_data_dir(tmp_path) -> None:
    legacy_path = tmp_path / "pittolog.sqlite"
    db_path = tmp_path / "data" / "pittolog.sqlite"
    legacy_path.write_bytes(b"legacy")

    migrate_legacy_database(legacy_path, db_path)

    assert db_path.read_bytes() == b"legacy"
    assert legacy_path.exists()


def test_migrate_legacy_database_keeps_existing_data_database(tmp_path) -> None:
    legacy_path = tmp_path / "pittolog.sqlite"
    db_path = tmp_path / "data" / "pittolog.sqlite"
    db_path.parent.mkdir()
    legacy_path.write_bytes(b"legacy")
    db_path.write_bytes(b"current")

    migrate_legacy_database(legacy_path, db_path)

    assert db_path.read_bytes() == b"current"


def test_migrate_legacy_databases_accepts_old_bbmanager_data_path(tmp_path) -> None:
    old_data_path = tmp_path / "data" / "bbmanager.sqlite"
    db_path = tmp_path / "data" / "pittolog.sqlite"
    old_data_path.parent.mkdir()
    old_data_path.write_bytes(b"old bbmanager")

    migrate_legacy_databases([tmp_path / "pittolog.sqlite", old_data_path, tmp_path / "bbmanager.sqlite"], db_path)

    assert db_path.read_bytes() == b"old bbmanager"
