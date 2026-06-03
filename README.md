# PittoLog

バーコード読み取りで物品の貸出・返却を管理する Windows スタンドアローン想定の Python アプリです。

## 方針

- GUI: PySide6
- DB: SQLite
- バーコード入力: LS2208 などの USB HID キーボード入力
- バーコード形式: Code128
- バーコード PNG 発行: Pillow による生成
- 貸出先: 部署
- 物品登録: カテゴリ選択 + 自動採番。必要時のみ手動バーコード指定
- 物品CSV読込: 未登録カテゴリは自動作成
- 部署登録: 自動採番。必要時のみ手動バーコード指定
- 返却操作: `ITEM:*` -> `ACTION:001`
- 貸出操作: `ITEM:*` -> `DEPT:*` -> `ACTION:001`

動作確認用の A4 バーコードPDFは [docs/assets/pittolog_test_barcodes_a4.pdf](docs/assets/pittolog_test_barcodes_a4.pdf) にあります。

操作方法は [docs/user_manual.md](docs/user_manual.md) を参照してください。

## 開発実行

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
pittolog
```

macOS/Linux では activate のパスだけ読み替えてください。

## テスト

```bash
pytest
```

## ライセンス

MIT License です。詳細は [LICENSE](LICENSE) を参照してください。
