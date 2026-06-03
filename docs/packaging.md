# 配布方式メモ

Windows で Python 未インストール環境へ配布する前提です。

## 初期方針

開発中は配布方式を固定しません。アプリの主要機能が固まった段階で、同じ Windows 環境で Nuitka と PyInstaller を比較します。

運用では exe 単体よりも、配布フォルダ単位で扱う方式を基本にします。DB と出力ファイルは利用者データなので、アップデート配布物で上書きしません。

```text
PittoLog/
  PittoLog.exe
  data/
    pittolog.sqlite
  backups/
  barcode_outputs/
```

アプリは標準で `data/pittolog.sqlite` を使用します。旧形式の `pittolog.sqlite`、`bbmanager.sqlite`、または `data/bbmanager.sqlite` があり、`data/pittolog.sqlite` がまだ存在しない場合は、初回起動時に `data/` へコピーします。

DB スキーマ更新に備えて、SQLite の `PRAGMA user_version` を使用します。既存 DB のバージョンがアプリの DB バージョンより古い場合、起動時に `backups/` へコピーしてから初期化・更新します。

アップデート時に差し替える対象:

- `PittoLog.exe`
- アプリ実行に必要なライブラリ、Qt plugin など
- README やドキュメント

アップデート時に残す対象:

- `data/pittolog.sqlite`
- `backups/`
- 出力済みの PNG/PDF/CSV

## Nuitka 候補

```bash
python -m pip install nuitka
python -m nuitka --mode=standalone --enable-plugin=pyside6 src/pittolog/main.py
```

`--mode=onefile` は配布しやすい一方で、起動時の展開コストやセキュリティソフトの誤検知を確認する必要があります。

## PyInstaller 候補

```bash
python -m pip install pyinstaller
pyinstaller --noconsole --name PittoLog src/pittolog/main.py
```

PyInstaller は検証しやすい反面、Qt 系 DLL と plugin を含むため配布サイズが大きくなりやすいです。

## 比較観点

- 配布フォルダまたは exe のサイズ
- 起動速度
- 別 Windows PC で Python なしに起動できるか
- バーコード PNG 発行が動くか
- SQLite DB ファイルを `data/` に作成できるか
- セキュリティソフトの誤検知が出ないか
