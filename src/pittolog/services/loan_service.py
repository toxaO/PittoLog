from __future__ import annotations

import csv
import sqlite3
from pathlib import Path


class LoanService:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def register_category(self, name: str) -> int:
        name = name.strip()
        if not name:
            raise ValueError("カテゴリ名を入力してください。")
        self.connection.execute(
            "INSERT OR IGNORE INTO categories(name) VALUES (?)",
            (name,),
        )
        self.connection.commit()
        row = self.connection.execute(
            "SELECT id FROM categories WHERE name = ?",
            (name,),
        ).fetchone()
        return int(row["id"])

    def list_categories(self) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                """
                SELECT id, name
                FROM categories
                ORDER BY name
                """
            )
        )

    def update_category(self, category_id: int, name: str) -> None:
        name = name.strip()
        if not name:
            raise ValueError("カテゴリ名を入力してください。")
        row = self.connection.execute(
            "SELECT id FROM categories WHERE name = ? AND id != ?",
            (name, category_id),
        ).fetchone()
        if row is not None:
            raise ValueError(f"カテゴリ「{name}」はすでに登録されています。別のカテゴリ名を入力してください。")
        self.connection.execute(
            "UPDATE categories SET name = ? WHERE id = ?",
            (name, category_id),
        )
        self.connection.commit()

    def get_setting_int(self, key: str, default: int) -> int:
        row = self.connection.execute(
            "SELECT value FROM app_settings WHERE key = ?",
            (key,),
        ).fetchone()
        if row is None:
            return default
        try:
            return int(row["value"])
        except ValueError:
            return default

    def get_setting(self, key: str, default: str = "") -> str:
        row = self.connection.execute(
            "SELECT value FROM app_settings WHERE key = ?",
            (key,),
        ).fetchone()
        return default if row is None else str(row["value"])

    def set_setting(self, key: str, value: str) -> None:
        self.connection.execute(
            """
            INSERT INTO app_settings(key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        self.connection.commit()

    def set_setting_int(self, key: str, value: int) -> None:
        self.connection.execute(
            """
            INSERT INTO app_settings(key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, str(value)),
        )
        self.connection.commit()

    def register_item(self, barcode: str, name: str, category_name: str = "") -> int:
        category_id = None
        if category_name.strip():
            category_id = self.register_category(category_name)
        return self.register_item_with_category(name, category_id, barcode)

    def register_item_with_category(self, name: str, category_id: int | None, barcode: str = "") -> int:
        barcode = self.next_item_barcode() if not barcode.strip() else normalize_registration_barcode(barcode, "ITEM:")
        name = name.strip()
        if not name:
            raise ValueError("物品名を入力してください。")

        if category_id is not None:
            row = self.connection.execute(
                "SELECT id FROM categories WHERE id = ?",
                (category_id,),
            ).fetchone()
            if row is None:
                raise ValueError("カテゴリを選択してください。")

        self._ensure_item_barcode_available(barcode)
        cursor = self.connection.execute(
            """
            INSERT INTO items(barcode, name, category_id)
            VALUES (?, ?, ?)
            """,
            (barcode, name, category_id),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def next_item_barcode(self) -> str:
        return self._next_barcode("items", "ITEM:", width=6)

    def get_item(self, item_id: int) -> sqlite3.Row:
        row = self.connection.execute(
            """
            SELECT id, barcode, name, category_id, active
            FROM items
            WHERE id = ?
            """,
            (item_id,),
        ).fetchone()
        if row is None:
            raise ValueError("物品が見つかりません。")
        return row

    def update_item(self, item_id: int, name: str, category_id: int | None, barcode: str | None = None) -> None:
        name = name.strip()
        if not name:
            raise ValueError("物品名を入力してください。")
        if category_id is not None:
            row = self.connection.execute(
                "SELECT id FROM categories WHERE id = ?",
                (category_id,),
            ).fetchone()
            if row is None:
                raise ValueError("カテゴリを選択してください。")
        if barcode is None:
            self.connection.execute(
                """
                UPDATE items
                SET name = ?, category_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (name, category_id, item_id),
            )
        else:
            normalized_barcode = normalize_registration_barcode(barcode, "ITEM:")
            self._ensure_item_barcode_available(normalized_barcode, item_id)
            self.connection.execute(
                """
                UPDATE items
                SET name = ?, category_id = ?, barcode = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (name, category_id, normalized_barcode, item_id),
            )
        self.connection.commit()

    def _ensure_item_barcode_available(self, barcode: str, item_id: int | None = None) -> None:
        row = self.connection.execute(
            """
            SELECT id, name
            FROM items
            WHERE active = 1 AND barcode = ? AND (? IS NULL OR id != ?)
            """,
            (barcode, item_id, item_id),
        ).fetchone()
        if row is not None:
            raise ValueError(f"{barcode} は、すでに別の物品「{row['name']}」で使われています。別のバーコードを指定してください。")

    def barcode_entries_for_item_ids(self, item_ids: list[int]) -> list[tuple[str, str]]:
        if not item_ids:
            raise ValueError("物品IDを指定してください。")
        entries: list[tuple[str, str]] = []
        for item_id in item_ids:
            item = self.get_item(item_id)
            if not item["active"]:
                raise ValueError(f"物品ID {item_id} は登録解除済みです。")
            if not item["barcode"]:
                raise ValueError(f"物品ID {item_id} にバーコードがありません。")
            entries.append((item["name"], item["barcode"]))
        return entries

    def import_items_csv(self, path: Path) -> int:
        with path.open("r", newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)
            if reader.fieldnames is None:
                raise ValueError("CSVにヘッダー行がありません。")
            count = 0
            for line_number, row in enumerate(reader, start=2):
                name = csv_value(row, "name", "物品名")
                category_name = csv_value(row, "category", "カテゴリ")
                barcode = csv_value(row, "barcode", "バーコード")
                if not name:
                    raise ValueError(f"{line_number}行目: 物品名が空です。")
                category_id = self.register_category(category_name) if category_name else None
                try:
                    self.register_item_with_category(name, category_id, barcode)
                except (sqlite3.Error, ValueError) as error:
                    raise ValueError(f"{line_number}行目: {error}") from error
                count += 1
        return count

    def register_department(self, barcode: str, name: str) -> int:
        barcode = normalize_registration_barcode(barcode, "DEPT:")
        return self.register_department_with_optional_barcode(name, barcode)

    def register_department_with_optional_barcode(self, name: str, barcode: str = "") -> int:
        barcode = self.next_department_barcode() if not barcode.strip() else normalize_registration_barcode(barcode, "DEPT:")
        name = name.strip()
        if not name:
            raise ValueError("部署名を入力してください。")
        self._ensure_department_barcode_available(barcode)
        cursor = self.connection.execute(
            "INSERT INTO departments(barcode, name) VALUES (?, ?)",
            (barcode, name),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def _ensure_department_barcode_available(self, barcode: str, department_id: int | None = None) -> None:
        row = self.connection.execute(
            """
            SELECT name
            FROM departments
            WHERE active = 1 AND barcode = ? AND (? IS NULL OR id != ?)
            """,
            (barcode, department_id, department_id),
        ).fetchone()
        if row is not None:
            raise ValueError(f"{barcode} は、すでに別の部署「{row['name']}」で使われています。別のバーコードを指定してください。")

    def next_department_barcode(self) -> str:
        return self._next_barcode("departments", "DEPT:", width=4)

    def _next_barcode(self, table: str, prefix: str, width: int) -> str:
        row = self.connection.execute(
            f"""
            SELECT barcode
            FROM {table}
            WHERE barcode IS NOT NULL AND barcode LIKE ?
            ORDER BY CAST(SUBSTR(barcode, ?) AS INTEGER) DESC
            LIMIT 1
            """,
            (f"{prefix}%", len(prefix) + 1),
        ).fetchone()
        number = 1 if row is None else parse_barcode_number(str(row["barcode"]), prefix) + 1
        return f"{prefix}{number:0{width}d}"

    def set_item_active(self, item_id: int, active: bool) -> None:
        if active:
            item = self.get_item(item_id)
            barcode = item["barcode"] or self.next_item_barcode()
            self.connection.execute(
                "UPDATE items SET active = 1, barcode = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (barcode, item_id),
            )
            self.connection.commit()
            return
        self.deactivate_item(item_id)

    def deactivate_item(self, item_id: int) -> None:
        if self._open_loan_for_item(item_id):
            raise ValueError("貸出中の物品は登録解除できません。")
        self.connection.execute(
            "UPDATE items SET active = 0, barcode = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (item_id,),
        )
        self.connection.commit()

    def deactivate_department(self, department_id: int) -> None:
        self.connection.execute(
            "UPDATE departments SET active = 0, barcode = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (department_id,),
        )
        self.connection.commit()

    def get_department(self, department_id: int) -> sqlite3.Row:
        row = self.connection.execute(
            """
            SELECT id, barcode, name
            FROM departments
            WHERE id = ? AND active = 1
            """,
            (department_id,),
        ).fetchone()
        if row is None:
            raise ValueError("部署が見つかりません。")
        return row

    def update_department(self, department_id: int, name: str, barcode: str | None = None) -> None:
        name = name.strip()
        if not name:
            raise ValueError("部署名を入力してください。")
        if barcode is None:
            self.connection.execute(
                "UPDATE departments SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (name, department_id),
            )
        else:
            normalized_barcode = normalize_registration_barcode(barcode, "DEPT:")
            self._ensure_department_barcode_available(normalized_barcode, department_id)
            self.connection.execute(
                "UPDATE departments SET name = ?, barcode = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (name, normalized_barcode, department_id),
            )
        self.connection.commit()

    def loan_item(self, item_barcode: str, department_barcode: str) -> str:
        item = self._active_item_by_barcode(item_barcode)
        department = self._active_department_by_barcode(department_barcode)
        if self._open_loan_for_item(int(item["id"])):
            raise ValueError(f"{item['name']} はすでに貸出中です。")

        self.connection.execute(
            "INSERT INTO loans(item_id, department_id) VALUES (?, ?)",
            (item["id"], department["id"]),
        )
        self.connection.execute(
            """
            INSERT INTO events(event_type, item_id, department_id, barcode, note)
            VALUES ('loan', ?, ?, ?, ?)
            """,
            (
                item["id"],
                department["id"],
                item["barcode"],
                f"{item['name']} -> {department['name']}",
            ),
        )
        self.connection.commit()
        return f"貸出完了: {item['name']} -> {department['name']}"

    def return_item(self, item_barcode: str) -> str:
        item = self._active_item_by_barcode(item_barcode)
        loan = self._open_loan_for_item(int(item["id"]))
        if not loan:
            raise ValueError(f"{item['name']} は貸出中ではありません。")

        self.connection.execute(
            "UPDATE loans SET returned_at = CURRENT_TIMESTAMP WHERE id = ?",
            (loan["id"],),
        )
        self.connection.execute(
            """
            INSERT INTO events(event_type, item_id, department_id, barcode, note)
            VALUES ('return', ?, ?, ?, ?)
            """,
            (
                item["id"],
                loan["department_id"],
                item["barcode"],
                f"{item['name']} returned",
            ),
        )
        self.connection.commit()
        return f"返却完了: {item['name']}"

    def list_items(
        self,
        query: str = "",
        sort_by: str = "id",
        sort_desc: bool = False,
        category_id: int | None = None,
        status: str = "",
        active_filter: str = "active",
        loan_department_id: int | None = None,
    ) -> list[sqlite3.Row]:
        sort_columns = {
            "id": "items.id",
            "name": "items.name",
            "barcode": "items.barcode",
            "category": "category",
            "status": "status",
        }
        order_column = sort_columns.get(sort_by, "items.id")
        order_direction = "DESC" if sort_desc else "ASC"
        where = "1 = 1"
        params: list[str | int] = []
        if category_id is not None:
            where += " AND items.category_id = ?"
            params.append(category_id)
        if status:
            where += """
                AND CASE
                    WHEN items.active = 0 THEN '登録解除'
                    WHEN loans.id IS NULL THEN '在庫'
                    ELSE '貸出中'
                END = ?
            """
            params.append(status)
        if active_filter == "active":
            where += " AND items.active = 1"
        elif active_filter == "inactive":
            where += " AND items.active = 0"
        if loan_department_id is not None:
            where += " AND loans.department_id = ?"
            params.append(loan_department_id)
        query = query.strip()
        if query:
            where += """
                AND (
                    CAST(items.id AS TEXT) LIKE ?
                    OR items.barcode LIKE ?
                    OR items.name LIKE ?
                    OR COALESCE(categories.name, '') LIKE ?
                    OR CASE
                        WHEN items.active = 0 THEN '登録解除'
                        WHEN loans.id IS NULL THEN '在庫'
                        ELSE '貸出中'
                    END LIKE ?
                    OR COALESCE(departments.name, '') LIKE ?
                )
            """
            like_query = f"%{query}%"
            params.extend([like_query] * 6)
        return list(
            self.connection.execute(
                f"""
                SELECT
                    items.id,
                    items.barcode,
                    items.name,
                    COALESCE(categories.name, '') AS category,
                    CASE WHEN items.active = 1 THEN '有効' ELSE '無効' END AS active_status,
                    CASE
                        WHEN items.active = 0 THEN '登録解除'
                        WHEN loans.id IS NULL THEN '在庫'
                        ELSE '貸出中'
                    END AS status,
                    COALESCE(departments.name, '') AS loan_department
                FROM items
                LEFT JOIN categories ON categories.id = items.category_id
                LEFT JOIN loans ON loans.item_id = items.id AND loans.returned_at IS NULL
                LEFT JOIN departments ON departments.id = loans.department_id
                WHERE {where}
                ORDER BY {order_column} {order_direction}, items.id ASC
                """,
                params,
            )
        )

    def list_departments(self) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                """
                SELECT id, barcode, name
                FROM departments
                WHERE active = 1
                ORDER BY id
                """
            )
        )

    def list_open_loans(
        self,
        query: str = "",
        sort_by: str = "loaned_at",
        sort_desc: bool = True,
        department_id: int | None = None,
        category_id: int | None = None,
    ) -> list[sqlite3.Row]:
        sort_columns = {
            "loaned_at": "loans.loaned_at",
            "item_name": "items.name",
            "item_barcode": "items.barcode",
            "department_name": "departments.name",
            "category": "category",
        }
        order_column = sort_columns.get(sort_by, "loans.loaned_at")
        order_direction = "DESC" if sort_desc else "ASC"
        where = "loans.returned_at IS NULL"
        params: list[str] = []
        query = query.strip()
        if query:
            where += """
                AND (
                    strftime('%Y/%m/%d %H:%M', loans.loaned_at, '+9 hours') LIKE ?
                    OR items.name LIKE ?
                    OR items.barcode LIKE ?
                    OR departments.name LIKE ?
                )
            """
            like_query = f"%{query}%"
            params.extend([like_query] * 4)
        if department_id is not None:
            where += " AND loans.department_id = ?"
            params.append(str(department_id))
        if category_id is not None:
            where += " AND items.category_id = ?"
            params.append(str(category_id))
        return list(
            self.connection.execute(
                f"""
                SELECT
                    strftime('%Y/%m/%d %H:%M', loans.loaned_at, '+9 hours') AS loaned_at,
                    items.name AS item_name,
                    COALESCE(categories.name, '') AS category,
                    items.barcode AS item_barcode,
                    departments.name AS department_name
                FROM loans
                JOIN items ON items.id = loans.item_id
                LEFT JOIN categories ON categories.id = items.category_id
                JOIN departments ON departments.id = loans.department_id
                WHERE {where}
                ORDER BY {order_column} {order_direction}, loans.id DESC
                """,
                params,
            )
        )

    def list_events(
        self,
        query: str = "",
        sort_by: str = "created_at",
        sort_desc: bool = True,
        date_from: str = "",
        date_to: str = "",
        event_type: str = "",
        department_id: int | None = None,
    ) -> list[sqlite3.Row]:
        sort_columns = {
            "created_at": "events.created_at",
            "event_type": "event_type",
            "item_name": "item_name",
            "department_name": "department_name",
            "note": "events.note",
        }
        order_column = sort_columns.get(sort_by, "events.created_at")
        order_direction = "DESC" if sort_desc else "ASC"
        where = "1 = 1"
        params: list[str] = []
        query = query.strip()
        if query:
            where += """
                AND (
                    events.event_type LIKE ?
                    OR CASE events.event_type WHEN 'loan' THEN '貸出' WHEN 'return' THEN '返却' ELSE events.event_type END LIKE ?
                    OR COALESCE(items.name, '') LIKE ?
                    OR COALESCE(departments.name, '') LIKE ?
                    OR COALESCE(events.note, '') LIKE ?
                    OR strftime('%Y-%m-%d %H:%M:%S', events.created_at, '+9 hours') LIKE ?
                )
            """
            like_query = f"%{query}%"
            params.extend([like_query] * 6)
        if date_from:
            where += " AND datetime(events.created_at, '+9 hours') >= ?"
            params.append(f"{date_from} 00:00:00")
        if date_to:
            where += " AND datetime(events.created_at, '+9 hours') <= ?"
            params.append(f"{date_to} 23:59:59")
        if event_type:
            where += " AND events.event_type = ?"
            params.append(event_type)
        if department_id is not None:
            where += " AND events.department_id = ?"
            params.append(str(department_id))
        return list(
            self.connection.execute(
                f"""
                SELECT
                    strftime('%Y-%m-%d %H:%M:%S', events.created_at, '+9 hours') AS created_at,
                    CASE events.event_type
                        WHEN 'loan' THEN '貸出'
                        WHEN 'return' THEN '返却'
                        ELSE events.event_type
                    END AS event_type,
                    COALESCE(items.name, '') AS item_name,
                    COALESCE(departments.name, '') AS department_name,
                    events.note
                FROM events
                LEFT JOIN items ON items.id = events.item_id
                LEFT JOIN departments ON departments.id = events.department_id
                WHERE {where}
                ORDER BY {order_column} {order_direction}, events.id DESC
                """,
                params,
            )
        )

    def export_csv(self, path: Path, rows: list[sqlite3.Row]) -> None:
        if not rows:
            path.write_text("", encoding="utf-8-sig")
            return
        with path.open("w", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(dict(row) for row in rows)

    def validate_item_barcode(self, barcode: str) -> sqlite3.Row:
        return self._active_item_by_barcode(barcode)

    def validate_department_barcode(self, barcode: str) -> sqlite3.Row:
        return self._active_department_by_barcode(barcode)

    def item_is_on_loan(self, barcode: str) -> bool:
        item = self._active_item_by_barcode(barcode)
        return self._open_loan_for_item(int(item["id"])) is not None

    def item_name_for_barcode(self, barcode: str) -> str:
        return str(self._active_item_by_barcode(barcode)["name"])

    def department_name_for_barcode(self, barcode: str) -> str:
        return str(self._active_department_by_barcode(barcode)["name"])

    def open_loan_department_name_for_item_barcode(self, barcode: str) -> str:
        item = self._active_item_by_barcode(barcode)
        loan = self._open_loan_for_item(int(item["id"]))
        if loan is None:
            return ""
        row = self.connection.execute(
            "SELECT name FROM departments WHERE id = ?",
            (loan["department_id"],),
        ).fetchone()
        return "" if row is None else str(row["name"])

    def barcode_display_label(self, barcode: str) -> str:
        normalized = normalize_barcode(barcode)
        if normalized == "ACTION:001":
            return "確認"
        if normalized == "ACTION:002":
            return "キャンセル"
        if normalized.startswith("ITEM:"):
            return self.item_name_for_barcode(normalized)
        if normalized.startswith("DEPT:"):
            return self.department_name_for_barcode(normalized)
        return normalized

    def barcode_targets(self, kind: str, category_id: int | None = None) -> list[tuple[str, str]]:
        if kind == "ITEM":
            where = "active = 1 AND barcode IS NOT NULL"
            params: list[int] = []
            if category_id is not None:
                where += " AND category_id = ?"
                params.append(category_id)
            rows = self.connection.execute(
                f"""
                SELECT name, barcode
                FROM items
                WHERE {where}
                ORDER BY name
                """,
                params,
            ).fetchall()
            return [(str(row["name"]), str(row["barcode"])) for row in rows]
        if kind == "DEPT":
            rows = self.connection.execute(
                """
                SELECT name, barcode
                FROM departments
                WHERE active = 1 AND barcode IS NOT NULL
                ORDER BY name
                """
            ).fetchall()
            return [(str(row["name"]), str(row["barcode"])) for row in rows]
        if kind == "ACTION":
            return [("確認", "ACTION:001"), ("キャンセル", "ACTION:002")]
        return []

    def _active_item_by_barcode(self, barcode: str) -> sqlite3.Row:
        barcode = normalize_barcode(barcode)
        require_prefix(barcode, "ITEM:")
        row = self.connection.execute(
            "SELECT * FROM items WHERE barcode = ? AND active = 1",
            (barcode,),
        ).fetchone()
        if row is None:
            raise ValueError(f"未登録の物品バーコードです: {barcode}")
        return row

    def _active_department_by_barcode(self, barcode: str) -> sqlite3.Row:
        barcode = normalize_barcode(barcode)
        require_prefix(barcode, "DEPT:")
        row = self.connection.execute(
            "SELECT * FROM departments WHERE barcode = ? AND active = 1",
            (barcode,),
        ).fetchone()
        if row is None:
            raise ValueError(f"未登録の部署バーコードです: {barcode}")
        return row

    def _open_loan_for_item(self, item_id: int) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM loans WHERE item_id = ? AND returned_at IS NULL",
            (item_id,),
        ).fetchone()


def normalize_barcode(value: str) -> str:
    normalized = "".join(value.strip().upper().split()).replace("：", ":").replace("＋", "+")
    if len(normalized) >= 3 and normalized.startswith("]C"):
        normalized = normalized[3:]
    for label in ("ITEM", "DEPT", "ACTION"):
        if normalized.startswith(label):
            suffix = normalized[len(label):]
            if suffix.startswith((":", "+", ";", "；")):
                suffix = suffix[1:]
            if suffix.startswith("+"):
                suffix = suffix[1:]
            if suffix and (suffix[0].isdigit() or label == "ACTION"):
                return f"{label}:{suffix}"
    return normalized


def normalize_registration_barcode(value: str, prefix: str) -> str:
    normalized = normalize_barcode(value)
    if normalized.startswith(prefix):
        return normalized

    label = prefix.removesuffix(":")
    if normalized.startswith(label) and not normalized.startswith(prefix):
        return f"{prefix}{normalized[len(label):].removeprefix(':')}"

    known_prefixes = ("ITEM:", "DEPT:", "ACTION:")
    if normalized.startswith(known_prefixes):
        expected = barcode_prefix_label(prefix)
        actual = barcode_prefix_label(normalized.split(":", 1)[0] + ":")
        raise ValueError(f"これは{actual}バーコードです。{expected}には {prefix} で始まるバーコードを使ってください。読み取り値: {normalized}")

    if normalized:
        return f"{prefix}{normalized}"

    raise ValueError(f"{prefix} で始まるバーコードを登録してください。読み取り値: 空")


def parse_barcode_number(barcode: str, prefix: str) -> int:
    normalized = normalize_barcode(barcode)
    require_prefix(normalized, prefix)
    suffix = normalized[len(prefix):]
    if not suffix.isdigit():
        raise ValueError(f"{prefix} の後ろは数字だけにしてください。読み取り値: {normalized}")
    return int(suffix)


def csv_value(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return value.strip()
    return ""


def require_prefix(value: str, prefix: str) -> None:
    if not value.startswith(prefix):
        shown = value or "空"
        raise ValueError(f"{barcode_prefix_label(prefix)}バーコードは {prefix} で始まる必要があります。読み取り値: {shown}")


def barcode_prefix_label(prefix: str) -> str:
    return {
        "ITEM:": "物品",
        "DEPT:": "部署",
        "ACTION:": "操作",
    }.get(prefix, prefix)
