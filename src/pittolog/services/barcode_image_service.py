from __future__ import annotations

from pathlib import Path
import unicodedata

from PIL import Image, ImageDraw, ImageFont

CODE128_PATTERNS = [
    "212222", "222122", "222221", "121223", "121322", "131222", "122213", "122312", "132212", "221213",
    "221312", "231212", "112232", "122132", "122231", "113222", "123122", "123221", "223211", "221132",
    "221231", "213212", "223112", "312131", "311222", "321122", "321221", "312212", "322112", "322211",
    "212123", "212321", "232121", "111323", "131123", "131321", "112313", "132113", "132311", "211313",
    "231113", "231311", "112133", "112331", "132131", "113123", "113321", "133121", "313121", "211331",
    "231131", "213113", "213311", "213131", "311123", "311321", "331121", "312113", "312311", "332111",
    "314111", "221411", "431111", "111224", "111422", "121124", "121421", "141122", "141221", "112214",
    "112412", "122114", "122411", "142112", "142211", "241211", "221114", "413111", "241112", "134111",
    "111242", "121142", "121241", "114212", "124112", "124211", "411212", "421112", "421211", "212141",
    "214121", "412121", "111143", "111341", "131141", "114113", "114311", "411113", "411311", "113141",
    "114131", "311141", "411131", "211412", "211214", "211232", "2331112",
]

START_B = 104
CODE_A = 101
STOP = 106
CARRIAGE_RETURN_CODE_A = 77
SHEET_COLUMNS = 2
SHEET_ROWS = 7

TEST_BARCODES = [
    ("確認", "ACTION:001"),
    ("キャンセル", "ACTION:002"),
    ("物品 1", "ITEM:000001"),
    ("物品 2", "ITEM:000002"),
    ("物品 3", "ITEM:000003"),
    ("物品 4", "ITEM:000004"),
    ("物品 5", "ITEM:000005"),
    ("物品 6", "ITEM:000006"),
    ("総務", "DEPT:0001"),
    ("経理", "DEPT:0002"),
    ("開発", "DEPT:0003"),
    ("営業", "DEPT:0004"),
]


def write_barcode_png(
    value: str,
    output_dir: Path,
    width_mm: float = 70.0,
    height_mm: float = 18.0,
    quiet_zone_mm: float = 4.0,
    show_text: bool = True,
    label_text: str = "",
) -> Path:
    barcode_value = normalize_code128_b(value)
    output_dir.mkdir(parents=True, exist_ok=True)
    image = render_code128_png(
        barcode_value,
        module_width_px=module_width_px_for_total_width(barcode_value, width_mm, append_enter=True),
        height_px=max(80, round(height_mm * 8)),
        quiet_zone_px=max(16, round(quiet_zone_mm * 8)),
        show_text=show_text,
        append_enter=True,
        label_text=label_text,
    )
    path = output_dir / f"{safe_filename(barcode_value)}.png"
    image.save(path)
    return path


def write_barcode_png_file(
    value: str,
    output_path: Path,
    width_mm: float = 70.0,
    height_mm: float = 18.0,
    quiet_zone_mm: float = 4.0,
    show_text: bool = True,
    label_text: str = "",
) -> Path:
    barcode_value = normalize_code128_b(value)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image = render_code128_png(
        barcode_value,
        module_width_px=module_width_px_for_total_width(barcode_value, width_mm, append_enter=True),
        height_px=max(80, round(height_mm * 8)),
        quiet_zone_px=max(16, round(quiet_zone_mm * 8)),
        show_text=show_text,
        append_enter=True,
        label_text=label_text,
    )
    image.save(output_path)
    return output_path


def write_test_sheet_png(output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image = render_barcode_sheet(TEST_BARCODES)
    image.save(output_path)
    return output_path


def write_test_sheet_pdf(
    output_path: Path,
    width_mm: float = 70.0,
    height_mm: float = 18.0,
    quiet_zone_mm: float = 4.0,
    columns: int = SHEET_COLUMNS,
) -> Path:
    return write_barcode_sheet_pdf(TEST_BARCODES, output_path, width_mm, height_mm, quiet_zone_mm, columns)


def write_barcode_sheet_png(entries: list[tuple[str, str]], output_path: Path) -> Path:
    if not entries:
        raise ValueError("バーコード一覧を入力してください。")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image = render_barcode_sheet(entries)
    image.save(output_path)
    return output_path


def write_barcode_sheet_pdf(
    entries: list[tuple[str, str]],
    output_path: Path,
    width_mm: float = 70.0,
    height_mm: float = 18.0,
    quiet_zone_mm: float = 4.0,
    columns: int = SHEET_COLUMNS,
) -> Path:
    if not entries:
        raise ValueError("バーコード一覧を入力してください。")
    capacity = sheet_page_capacity(columns)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pages = [
        render_barcode_sheet(
            page_entries,
            page_number=index + 1,
            page_count=(len(entries) + capacity - 1) // capacity,
            width_mm=width_mm,
            height_mm=height_mm,
            quiet_zone_mm=quiet_zone_mm,
            columns=columns,
        )
        for index, page_entries in enumerate(chunk_entries(entries, capacity))
    ]
    pages[0].save(output_path, "PDF", save_all=True, append_images=pages[1:], resolution=300)
    return output_path


def render_barcode_sheet(
    entries: list[tuple[str, str]],
    page_number: int = 1,
    page_count: int = 1,
    width_mm: float = 70.0,
    height_mm: float = 18.0,
    quiet_zone_mm: float = 4.0,
    columns: int = SHEET_COLUMNS,
) -> Image.Image:
    capacity = sheet_page_capacity(columns)
    width, height = 2480, 3508
    margin = 140
    title_height = 150
    cell_width = (width - margin * 2) // columns
    cell_height = (height - margin * 2 - title_height) // SHEET_ROWS

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = load_font(58)
    label_font = load_font(36)
    value_font = load_font(30)
    draw.text((margin, margin), "PittoLog 動作テスト用バーコード", fill="black", font=title_font)
    draw.text((margin, margin + 78), "A4 / Code128 / Enter付き / 印刷倍率 100% 推奨", fill="black", font=value_font)
    if page_count > 1:
        page_text = f"{page_number} / {page_count}"
        bbox = draw.textbbox((0, 0), page_text, font=value_font)
        draw.text((width - margin - (bbox[2] - bbox[0]), margin + 78), page_text, fill="black", font=value_font)

    for index, (label, value) in enumerate(entries[:capacity]):
        row = index // columns
        column = index % columns
        x = margin + column * cell_width
        y = margin + title_height + row * cell_height
        draw.rounded_rectangle((x + 10, y + 10, x + cell_width - 20, y + cell_height - 18), radius=8, outline="#999999", width=2)
        draw.text((x + 38, y + 34), label, fill="black", font=label_font)
        draw.text((x + 38, y + 82), f"{value} + Enter", fill="#333333", font=value_font)
        barcode = render_code128_png(
            value,
            module_width_px=module_width_px_for_total_width(value, width_mm, append_enter=True),
            height_px=max(80, round(height_mm * 8)),
            quiet_zone_px=max(16, round(quiet_zone_mm * 8)),
            show_text=False,
            append_enter=True,
        )
        target_width = cell_width - 96
        if barcode.width > target_width:
            ratio = target_width / barcode.width
            barcode = barcode.resize((target_width, max(1, round(barcode.height * ratio))), Image.Resampling.NEAREST)
        image.paste(barcode, (x + 48, y + 132))
    return image


def chunk_entries(entries: list[tuple[str, str]], size: int) -> list[list[tuple[str, str]]]:
    return [entries[index:index + size] for index in range(0, len(entries), size)]


def sheet_page_capacity(columns: int) -> int:
    if columns < 1 or columns > 4:
        raise ValueError("A4まとめPDFの列数は1から4の範囲で指定してください。")
    return columns * SHEET_ROWS


def render_code128_png(
    value: str,
    module_width_px: int,
    height_px: int,
    quiet_zone_px: int,
    show_text: bool,
    append_enter: bool = False,
    label_text: str = "",
) -> Image.Image:
    modules = code128_b_modules(value, append_enter)
    label_height = 42 if label_text else 0
    text_height = 44 if show_text else 0
    width = len(modules) * module_width_px + quiet_zone_px * 2
    image = Image.new("RGB", (width, label_height + height_px + text_height), "white")
    draw = ImageDraw.Draw(image)
    if label_text:
        label_font = load_font(24)
        label_bbox = draw.textbbox((0, 0), label_text, font=label_font)
        label_width = label_bbox[2] - label_bbox[0]
        draw.text((max(0, (width - label_width) // 2), 8), label_text, fill="black", font=label_font)
    x = quiet_zone_px
    for is_bar in modules:
        if is_bar:
            draw.rectangle((x, label_height, x + module_width_px - 1, label_height + height_px - 1), fill="black")
        x += module_width_px
    if show_text:
        font = load_font(24)
        bbox = draw.textbbox((0, 0), value, font=font)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width) // 2, label_height + height_px + 8), value, fill="black", font=font)
    return image


def module_width_px_for_total_width(value: str, width_mm: float, append_enter: bool = False) -> int:
    modules = code128_b_modules(value, append_enter)
    target_width_px = max(1, round(width_mm * 8))
    return max(1, round(target_width_px / len(modules)))


def code128_b_modules(value: str, append_enter: bool = False) -> list[bool]:
    normalized = normalize_code128_b(value)
    codes = [START_B]
    codes.extend(ord(character) - 32 for character in normalized)
    if append_enter:
        codes.extend([CODE_A, CARRIAGE_RETURN_CODE_A])
    checksum = codes[0]
    for index, code in enumerate(codes[1:], start=1):
        checksum += code * index
    codes.append(checksum % 103)
    codes.append(STOP)

    modules: list[bool] = []
    for code in codes:
        is_bar = True
        for width in CODE128_PATTERNS[code]:
            modules.extend([is_bar] * int(width))
            is_bar = not is_bar
    return modules


def normalize_code128_b(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().upper()
    if not normalized:
        raise ValueError("バーコード値を入力してください。")
    if any(ord(character) < 32 or ord(character) > 126 for character in normalized):
        raise ValueError("Code128 の値は半角英数字と記号で入力してください。")
    return normalized


def safe_filename(value: str) -> str:
    return value.replace(":", "_").replace("/", "_").replace("\\", "_")


def load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()
