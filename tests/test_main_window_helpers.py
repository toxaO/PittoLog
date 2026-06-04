from __future__ import annotations

from pittolog.ui.main_window import parse_int_range, parse_positive_float, parse_sheet_entries, scan_mode_title, scan_selection_text


def test_parse_sheet_entries_accepts_comma_and_tab() -> None:
    entries = parse_sheet_entries("物品1,ITEM:000001\n確認\tACTION:001\nACTION:002")

    assert entries == [
        ("物品1", "ITEM:000001"),
        ("確認", "ACTION:001"),
        ("ACTION:002", "ACTION:002"),
    ]


def test_parse_sheet_entries_converts_fullwidth_barcode_values() -> None:
    entries = parse_sheet_entries("総務,ＤＥＰＴ：０００１\n確認,ＡＣＴＩＯＮ：００１")

    assert entries == [
        ("総務", "DEPT:0001"),
        ("確認", "ACTION:001"),
    ]


def test_parse_positive_float_uses_japanese_message() -> None:
    try:
        parse_positive_float("abc", "線幅 mm")
    except ValueError as error:
        assert str(error) == "線幅 mmは数字で入力してください。入力値: abc"
    else:
        raise AssertionError("文字列を数値として受け付けています。")


def test_parse_positive_float_rejects_zero() -> None:
    try:
        parse_positive_float("0", "高さ mm")
    except ValueError as error:
        assert str(error) == "高さ mmは0より大きい数字で入力してください。入力値: 0"
    else:
        raise AssertionError("0を正の数として受け付けています。")


def test_parse_int_range_accepts_digits_only() -> None:
    assert parse_int_range("60", "処理結果を表示する時間", 10, 1800) == 60


def test_parse_int_range_rejects_non_digits() -> None:
    try:
        parse_int_range("60秒", "処理結果を表示する時間", 10, 1800)
    except ValueError as error:
        assert str(error) == "処理結果を表示する時間は数字だけで入力してください。入力値: 60秒"
    else:
        raise AssertionError("数字以外を受け付けています。")


def test_scan_selection_text_shows_item_and_department() -> None:
    assert scan_selection_text("物品1", "総務") == "物品1 : 総務"
    assert scan_selection_text("物品1", None) == "物品1"


def test_scan_mode_title_uses_flow_names() -> None:
    assert scan_mode_title("item") == "貸出・返却 物品スキャン"
    assert scan_mode_title("loan") == "貸出先スキャン"
    assert scan_mode_title("confirm") == "貸出確認"
    assert scan_mode_title("return") == "返却確認"
    assert scan_mode_title("error") == "エラー"
