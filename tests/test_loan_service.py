from __future__ import annotations

from pittolog.db import connect, initialize_database
from pittolog.services.loan_service import LoanService, normalize_barcode


def make_service(tmp_path) -> LoanService:
    connection = connect(tmp_path / "test.sqlite")
    initialize_database(connection)
    return LoanService(connection)


def test_loan_and_return_item(tmp_path) -> None:
    service = make_service(tmp_path)
    service.register_item("ITEM:000001", "プロジェクター", "AV機器")
    service.register_department("DEPT:0001", "総務")

    loan_message = service.loan_item("ITEM:000001", "DEPT:0001")
    assert loan_message == "貸出完了: プロジェクター -> 総務"
    open_loans = service.list_open_loans()
    assert len(open_loans) == 1
    assert list(open_loans[0].keys()) == ["loaned_at", "item_name", "category", "item_barcode", "department_name"]

    return_message = service.return_item("ITEM:000001")
    assert return_message == "返却完了: プロジェクター"
    assert service.list_open_loans() == []


def test_list_open_loans_can_query_and_sort(tmp_path) -> None:
    service = make_service(tmp_path)
    service.register_item("ITEM:000001", "プロジェクター")
    service.register_department("DEPT:0001", "総務")
    service.loan_item("ITEM:000001", "DEPT:0001")

    rows = service.list_open_loans(query="総務", sort_by="item_name", sort_desc=False)

    assert len(rows) == 1
    assert rows[0]["item_name"] == "プロジェクター"
    assert service.list_open_loans(query="該当なし") == []


def test_list_open_loans_can_filter_by_department(tmp_path) -> None:
    service = make_service(tmp_path)
    service.register_item("ITEM:000001", "プロジェクター")
    service.register_item("ITEM:000002", "スクリーン")
    first_department_id = service.register_department("DEPT:0001", "総務")
    second_department_id = service.register_department("DEPT:0002", "経理")
    service.loan_item("ITEM:000001", "DEPT:0001")
    service.loan_item("ITEM:000002", "DEPT:0002")

    rows = service.list_open_loans(department_id=second_department_id)

    assert first_department_id != second_department_id
    assert [row["department_name"] for row in rows] == ["経理"]


def test_list_open_loans_can_filter_by_category(tmp_path) -> None:
    service = make_service(tmp_path)
    av_category_id = service.register_category("AV機器")
    office_category_id = service.register_category("事務用品")
    service.register_item_with_category("プロジェクター", av_category_id, "ITEM:000001")
    service.register_item_with_category("ホワイトボード", office_category_id, "ITEM:000002")
    service.register_department("DEPT:0001", "総務")
    service.loan_item("ITEM:000001", "DEPT:0001")
    service.loan_item("ITEM:000002", "DEPT:0001")

    rows = service.list_open_loans(category_id=av_category_id)

    assert [(row["item_name"], row["category"]) for row in rows] == [("プロジェクター", "AV機器")]


def test_cannot_loan_same_item_twice(tmp_path) -> None:
    service = make_service(tmp_path)
    service.register_item("ITEM:000001", "プロジェクター")
    service.register_department("DEPT:0001", "総務")
    service.loan_item("ITEM:000001", "DEPT:0001")

    try:
        service.loan_item("ITEM:000001", "DEPT:0001")
    except ValueError as error:
        assert "すでに貸出中" in str(error)
    else:
        raise AssertionError("貸出中の物品が再貸出できています。")


def test_cannot_return_item_not_on_loan(tmp_path) -> None:
    service = make_service(tmp_path)
    service.register_item("ITEM:000001", "プロジェクター")

    try:
        service.return_item("ITEM:000001")
    except ValueError as error:
        assert "貸出中ではありません" in str(error)
    else:
        raise AssertionError("未貸出の物品が返却できています。")


def test_registration_accepts_number_without_prefix(tmp_path) -> None:
    service = make_service(tmp_path)

    service.register_item("000001", "プロジェクター")
    service.register_department("0001", "総務")

    assert service.loan_item("ITEM:000001", "DEPT:0001") == "貸出完了: プロジェクター -> 総務"


def test_registration_accepts_scanner_symbology_prefix(tmp_path) -> None:
    service = make_service(tmp_path)

    service.register_item("]C0ITEM:000001", "プロジェクター")
    service.register_department("]C0DEPT:0001", "総務")

    assert service.loan_item("ITEM:000001", "DEPT:0001") == "貸出完了: プロジェクター -> 総務"


def test_registration_accepts_plus_separator_from_scanner(tmp_path) -> None:
    service = make_service(tmp_path)

    service.register_item("ITEM+000001", "プロジェクター")
    service.register_department("DEPT+0001", "総務")

    assert service.loan_item("ITEM+000001", "DEPT+0001") == "貸出完了: プロジェクター -> 総務"


def test_normalize_barcode_accepts_action_plus_separator_and_control_spaces() -> None:
    assert normalize_barcode("ACTION+001") == "ACTION:001"
    assert normalize_barcode("ACTION＋002\r\n") == "ACTION:002"
    assert normalize_barcode("]C0ACTION+001") == "ACTION:001"


def test_normalize_barcode_converts_fullwidth_numbers_and_letters() -> None:
    assert normalize_barcode("ＩＴＥＭ：０００００１") == "ITEM:000001"
    assert normalize_barcode("ＤＥＰＴ＋０００１") == "DEPT:0001"
    assert normalize_barcode("ＡＣＴＩＯＮ：００１") == "ACTION:001"


def test_registration_strips_plus_after_prefix_separator(tmp_path) -> None:
    service = make_service(tmp_path)

    service.register_item("ITEM:+000001", "プロジェクター")
    service.register_department("DEPT:+0001", "総務")

    items = service.list_items()
    departments = service.list_departments()
    assert items[0]["barcode"] == "ITEM:000001"
    assert departments[0]["barcode"] == "DEPT:0001"


def test_register_item_with_category_assigns_next_barcode(tmp_path) -> None:
    service = make_service(tmp_path)
    category_id = service.register_category("AV機器")

    first_id = service.register_item_with_category("プロジェクター", category_id)
    second_id = service.register_item_with_category("スクリーン", category_id)

    items = service.list_items()
    assert first_id == 1
    assert second_id == 2
    assert [item["barcode"] for item in items] == ["ITEM:000001", "ITEM:000002"]
    assert all(item["category"] == "AV機器" for item in items)


def test_register_item_with_category_allows_optional_manual_barcode(tmp_path) -> None:
    service = make_service(tmp_path)
    category_id = service.register_category("AV機器")

    service.register_item_with_category("プロジェクター", category_id, "ITEM:+000123")

    assert service.list_items()[0]["barcode"] == "ITEM:000123"


def test_list_items_can_sort_by_name_and_barcode(tmp_path) -> None:
    service = make_service(tmp_path)
    category_id = service.register_category("AV機器")
    service.register_item_with_category("スクリーン", category_id, "ITEM:000002")
    service.register_item_with_category("プロジェクター", category_id, "ITEM:000001")

    by_name = service.list_items(sort_by="name")
    by_barcode_desc = service.list_items(sort_by="barcode", sort_desc=True)

    assert [item["name"] for item in by_name] == ["スクリーン", "プロジェクター"]
    assert [item["barcode"] for item in by_barcode_desc] == ["ITEM:000002", "ITEM:000001"]


def test_list_items_can_filter_by_category_and_status(tmp_path) -> None:
    service = make_service(tmp_path)
    av_category_id = service.register_category("AV機器")
    office_category_id = service.register_category("事務用品")
    service.register_item_with_category("プロジェクター", av_category_id, "ITEM:000001")
    service.register_item_with_category("ホワイトボード", office_category_id, "ITEM:000002")
    service.register_department("DEPT:0001", "総務")
    service.loan_item("ITEM:000001", "DEPT:0001")

    av_items = service.list_items(query="AV")
    loaned_items = service.list_items(query="貸出中", sort_by="status")

    assert [item["name"] for item in av_items] == ["プロジェクター"]
    assert [item["name"] for item in loaned_items] == ["プロジェクター"]


def test_register_department_assigns_next_barcode(tmp_path) -> None:
    service = make_service(tmp_path)

    first_id = service.register_department_with_optional_barcode("総務")
    second_id = service.register_department_with_optional_barcode("経理")

    departments = service.list_departments()
    assert first_id == 1
    assert second_id == 2
    assert [department["barcode"] for department in departments] == ["DEPT:0001", "DEPT:0002"]


def test_register_department_allows_optional_manual_barcode(tmp_path) -> None:
    service = make_service(tmp_path)

    service.register_department_with_optional_barcode("総務", "DEPT:+0123")

    assert service.list_departments()[0]["barcode"] == "DEPT:0123"


def test_register_department_duplicate_barcode_uses_user_friendly_message(tmp_path) -> None:
    service = make_service(tmp_path)
    service.register_department_with_optional_barcode("総務", "DEPT:0001")

    try:
        service.register_department_with_optional_barcode("経理", "DEPT:0001")
    except ValueError as error:
        message = str(error)
        assert "すでに別の部署" in message
        assert "総務" in message
        assert "別のバーコードを指定してください" in message
    else:
        raise AssertionError("重複部署バーコードを登録できています。")


def test_update_department_changes_name_and_optional_barcode(tmp_path) -> None:
    service = make_service(tmp_path)
    department_id = service.register_department_with_optional_barcode("総務", "DEPT:0001")

    service.update_department(department_id, "経理", "DEPT:0002")

    department = service.list_departments()[0]
    assert department["name"] == "経理"
    assert department["barcode"] == "DEPT:0002"


def test_update_department_rejects_duplicate_barcode(tmp_path) -> None:
    service = make_service(tmp_path)
    service.register_department_with_optional_barcode("総務", "DEPT:0001")
    department_id = service.register_department_with_optional_barcode("経理", "DEPT:0002")

    try:
        service.update_department(department_id, "経理", "DEPT:0001")
    except ValueError as error:
        assert "すでに別の部署" in str(error)
    else:
        raise AssertionError("重複部署バーコードを変更で受け付けています。")


def test_deactivate_item_clears_barcode_and_allows_manual_reuse(tmp_path) -> None:
    service = make_service(tmp_path)
    category_id = service.register_category("AV機器")
    item_id = service.register_item_with_category("プロジェクター", category_id)

    service.deactivate_item(item_id)
    service.register_item_with_category("スクリーン", category_id, "ITEM:000001")

    assert service.list_items(query="スクリーン")[0]["barcode"] == "ITEM:000001"


def test_list_items_includes_inactive_and_can_filter_status(tmp_path) -> None:
    service = make_service(tmp_path)
    category_id = service.register_category("AV機器")
    active_id = service.register_item_with_category("プロジェクター", category_id)
    inactive_id = service.register_item_with_category("スクリーン", category_id)

    service.deactivate_item(inactive_id)

    active_items = service.list_items()
    all_items = service.list_items(active_filter="")
    inactive_items = service.list_items(status="登録解除", active_filter="inactive")

    assert [item["id"] for item in active_items] == [active_id]
    assert [item["id"] for item in all_items] == [active_id, inactive_id]
    assert [(item["name"], item["status"]) for item in inactive_items] == [("スクリーン", "登録解除")]
    assert inactive_items[0]["active_status"] == "無効"


def test_set_item_active_reactivates_with_next_barcode(tmp_path) -> None:
    service = make_service(tmp_path)
    category_id = service.register_category("AV機器")
    first_id = service.register_item_with_category("プロジェクター", category_id)
    service.register_item_with_category("スクリーン", category_id)

    service.set_item_active(first_id, False)
    service.set_item_active(first_id, True)

    row = service.get_item(first_id)
    assert row["active"] == 1
    assert row["barcode"] == "ITEM:000003"


def test_list_items_can_filter_by_category_combo_value(tmp_path) -> None:
    service = make_service(tmp_path)
    av_category_id = service.register_category("AV機器")
    office_category_id = service.register_category("事務用品")
    service.register_item_with_category("プロジェクター", av_category_id)
    service.register_item_with_category("ホワイトボード", office_category_id)

    rows = service.list_items(category_id=office_category_id)

    assert [row["name"] for row in rows] == ["ホワイトボード"]


def test_next_item_barcode_uses_max_existing_value_after_deactivation(tmp_path) -> None:
    service = make_service(tmp_path)
    category_id = service.register_category("AV機器")
    item_id = service.register_item_with_category("プロジェクター", category_id)

    service.deactivate_item(item_id)

    assert service.next_item_barcode() == "ITEM:000001"


def test_deactivate_department_clears_barcode_and_allows_manual_reuse(tmp_path) -> None:
    service = make_service(tmp_path)
    department_id = service.register_department_with_optional_barcode("総務")

    service.deactivate_department(department_id)
    service.register_department_with_optional_barcode("経理", "DEPT:0001")

    assert service.list_departments()[0]["barcode"] == "DEPT:0001"
    assert service.list_departments()[0]["name"] == "経理"


def test_next_department_barcode_uses_max_existing_value_after_deactivation(tmp_path) -> None:
    service = make_service(tmp_path)
    department_id = service.register_department_with_optional_barcode("総務")

    service.deactivate_department(department_id)

    assert service.next_department_barcode() == "DEPT:0001"


def test_manual_high_barcode_advances_next_default(tmp_path) -> None:
    service = make_service(tmp_path)
    category_id = service.register_category("AV機器")

    service.register_item_with_category("プロジェクター", category_id, "ITEM:000123")
    service.register_department_with_optional_barcode("総務", "DEPT:0123")

    assert service.next_item_barcode() == "ITEM:000124"
    assert service.next_department_barcode() == "DEPT:0124"


def test_import_items_csv_registers_new_categories(tmp_path) -> None:
    service = make_service(tmp_path)
    csv_path = tmp_path / "items.csv"
    csv_path.write_text(
        "物品名,カテゴリ,バーコード\n"
        "プロジェクター,AV機器,\n"
        "スクリーン,AV機器,ITEM:000010\n"
        "机,備品,\n",
        encoding="utf-8-sig",
    )

    count = service.import_items_csv(csv_path)

    items = service.list_items()
    categories = service.list_categories()
    assert count == 3
    assert [item["barcode"] for item in items] == ["ITEM:000001", "ITEM:000010", "ITEM:000011"]
    assert [category["name"] for category in categories] == ["AV機器", "備品"]


def test_import_items_csv_duplicate_barcode_includes_line_number(tmp_path) -> None:
    service = make_service(tmp_path)
    service.register_item("ITEM:000001", "登録済み")
    csv_path = tmp_path / "items.csv"
    csv_path.write_text(
        "物品名,カテゴリ,バーコード\n"
        "プロジェクター,AV機器,ITEM:000001\n",
        encoding="utf-8-sig",
    )

    try:
        service.import_items_csv(csv_path)
    except ValueError as error:
        message = str(error)
        assert message.startswith("2行目:")
        assert "すでに別の物品" in message
    else:
        raise AssertionError("重複バーコードを含むCSVを読み込めています。")


def test_update_item_and_category(tmp_path) -> None:
    service = make_service(tmp_path)
    old_category_id = service.register_category("旧カテゴリ")
    new_category_id = service.register_category("新カテゴリ")
    item_id = service.register_item_with_category("旧物品名", old_category_id)

    service.update_category(old_category_id, "変更後カテゴリ")
    service.update_item(item_id, "変更後物品名", new_category_id, "ITEM:000123")

    item = service.list_items()[0]
    categories = service.list_categories()
    assert item["name"] == "変更後物品名"
    assert item["category"] == "新カテゴリ"
    assert item["barcode"] == "ITEM:000123"
    assert [category["name"] for category in categories] == ["変更後カテゴリ", "新カテゴリ"]


def test_update_item_duplicate_barcode_uses_user_friendly_message(tmp_path) -> None:
    service = make_service(tmp_path)
    category_id = service.register_category("test")
    service.register_item_with_category("物品1", category_id, "ITEM:000001")
    second_id = service.register_item_with_category("物品2", category_id, "ITEM:000002")

    try:
        service.update_item(second_id, "物品2", category_id, "ITEM:000001")
    except ValueError as error:
        message = str(error)
        assert "すでに別の物品" in message
        assert "物品1" in message
        assert "別のバーコードを指定してください" in message
    else:
        raise AssertionError("重複バーコードを登録できています。")


def test_list_events_can_query_sort_and_filter_date_range(tmp_path) -> None:
    service = make_service(tmp_path)
    service.register_item("ITEM:000001", "プロジェクター")
    service.register_department("DEPT:0001", "総務")
    service.loan_item("ITEM:000001", "DEPT:0001")

    rows = service.list_events(query="プロジェクター", sort_by="item_name", sort_desc=False, date_from="2000-01-01", date_to="2999-12-31")

    assert len(rows) == 1
    assert rows[0]["item_name"] == "プロジェクター"
    assert rows[0]["department_name"] == "総務"
    assert rows[0]["created_at"].count(":") == 2
    assert service.list_events(date_from="2999-01-01") == []


def test_list_events_can_filter_by_operation_and_department(tmp_path) -> None:
    service = make_service(tmp_path)
    service.register_item("ITEM:000001", "プロジェクター")
    service.register_item("ITEM:000002", "スクリーン")
    service.register_department("DEPT:0001", "総務")
    department_id = service.register_department("DEPT:0002", "経理")
    service.loan_item("ITEM:000001", "DEPT:0001")
    service.loan_item("ITEM:000002", "DEPT:0002")
    service.return_item("ITEM:000002")

    rows = service.list_events(event_type="return", department_id=department_id)

    assert [(row["event_type"], row["department_name"]) for row in rows] == [("返却", "経理")]


def test_barcode_entries_for_item_ids(tmp_path) -> None:
    service = make_service(tmp_path)
    category_id = service.register_category("test")
    first_id = service.register_item_with_category("物品1", category_id)
    second_id = service.register_item_with_category("物品2", category_id)

    entries = service.barcode_entries_for_item_ids([second_id, first_id])

    assert entries == [
        ("物品2", "ITEM:000002"),
        ("物品1", "ITEM:000001"),
    ]


def test_barcode_display_label_returns_registered_name_or_action(tmp_path) -> None:
    service = make_service(tmp_path)
    service.register_item("ITEM:000001", "プロジェクター")
    service.register_department("DEPT:0001", "総務")

    assert service.barcode_display_label("ITEM:000001") == "プロジェクター"
    assert service.barcode_display_label("DEPT:0001") == "総務"
    assert service.barcode_display_label("ACTION:001") == "確認"


def test_barcode_targets_can_filter_items_by_category(tmp_path) -> None:
    service = make_service(tmp_path)
    av_category_id = service.register_category("AV機器")
    office_category_id = service.register_category("事務用品")
    service.register_item_with_category("プロジェクター", av_category_id, "ITEM:000001")
    service.register_item_with_category("ホワイトボード", office_category_id, "ITEM:000002")

    assert service.barcode_targets("ITEM", av_category_id) == [("プロジェクター", "ITEM:000001")]
