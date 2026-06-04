from __future__ import annotations

from pittolog.services.barcode_image_service import code128_b_modules, module_width_px_for_total_width, normalize_code128_b, sheet_page_capacity, write_barcode_sheet_pdf, write_barcode_sheet_png, write_test_sheet_pdf, write_test_sheet_png


def test_code128_modules_are_generated() -> None:
    modules = code128_b_modules("ACTION:001")

    assert modules
    assert any(modules)
    assert not all(modules)


def test_code128_modules_can_append_enter() -> None:
    plain_modules = code128_b_modules("ACTION:001")
    enter_modules = code128_b_modules("ACTION:001", append_enter=True)

    assert len(enter_modules) > len(plain_modules)


def test_code128_value_converts_fullwidth_numbers_and_letters() -> None:
    assert normalize_code128_b("ＡＣＴＩＯＮ：００１") == "ACTION:001"


def test_module_width_uses_total_barcode_width() -> None:
    narrow = module_width_px_for_total_width("ITEM:000001", 40, append_enter=True)
    wide = module_width_px_for_total_width("ITEM:000001", 80, append_enter=True)

    assert wide > narrow


def test_sheet_page_capacity_uses_columns() -> None:
    assert sheet_page_capacity(1) == 7
    assert sheet_page_capacity(3) == 21


def test_sheet_page_capacity_rejects_out_of_range_columns() -> None:
    try:
        sheet_page_capacity(5)
    except ValueError as error:
        assert str(error) == "A4まとめPDFの列数は1から4の範囲で指定してください。"
    else:
        raise AssertionError("範囲外の列数を受け付けています。")


def test_write_test_sheet_png(tmp_path) -> None:
    path = write_test_sheet_png(tmp_path / "sheet.png")

    assert path.exists()
    assert path.stat().st_size > 0


def test_write_test_sheet_pdf(tmp_path) -> None:
    path = write_test_sheet_pdf(tmp_path / "sheet.pdf")

    assert path.exists()
    assert path.stat().st_size > 0


def test_write_barcode_sheet_png(tmp_path) -> None:
    path = write_barcode_sheet_png(
        [
            ("物品1", "ITEM:000001"),
            ("確認", "ACTION:001"),
        ],
        tmp_path / "custom_sheet.png",
    )

    assert path.exists()
    assert path.stat().st_size > 0


def test_write_barcode_sheet_pdf_multiple_pages(tmp_path) -> None:
    entries = [(f"物品{index}", f"ITEM:{index:06d}") for index in range(1, 18)]

    path = write_barcode_sheet_pdf(entries, tmp_path / "custom_sheet.pdf")

    assert path.exists()
    assert path.stat().st_size > 0


def test_write_barcode_sheet_pdf_accepts_custom_size(tmp_path) -> None:
    path = write_barcode_sheet_pdf([("物品1", "ITEM:000001")], tmp_path / "custom_size.pdf", 60, 24, 5)

    assert path.exists()
    assert path.stat().st_size > 0


def test_write_barcode_sheet_pdf_accepts_columns(tmp_path) -> None:
    path = write_barcode_sheet_pdf([("物品1", "ITEM:000001")], tmp_path / "custom_columns.pdf", columns=3)

    assert path.exists()
    assert path.stat().st_size > 0
