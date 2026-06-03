from __future__ import annotations

from pittolog.db import CURRENT_DB_VERSION, connect, get_user_version, initialize_database, prepare_database


def test_initialize_database_normalizes_existing_plus_barcodes(tmp_path) -> None:
    connection = connect(tmp_path / "test.sqlite")
    initialize_database(connection)
    connection.execute(
        "INSERT INTO departments(barcode, name) VALUES ('DEPT:+0001', '総務')",
    )
    connection.commit()

    initialize_database(connection)

    row = connection.execute("SELECT barcode FROM departments WHERE name = '総務'").fetchone()
    assert row["barcode"] == "DEPT:0001"


def test_prepare_database_sets_version_and_backs_up_old_database(tmp_path) -> None:
    db_path = tmp_path / "data" / "pittolog.sqlite"
    db_path.parent.mkdir()
    connection = connect(db_path)
    initialize_database(connection)
    connection.execute("INSERT INTO categories(name) VALUES ('test')")
    connection.commit()
    connection.close()

    prepared = prepare_database(db_path)

    assert get_user_version(prepared) == CURRENT_DB_VERSION
    assert prepared.execute("SELECT name FROM categories").fetchone()["name"] == "test"
    prepared.close()
    backups = list((tmp_path / "backups").glob("pittolog_*.sqlite"))
    assert len(backups) == 1
