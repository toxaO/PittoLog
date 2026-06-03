# AGENTS_PROJECT.md

このファイルは、そのプロジェクト固有の AI agent 向け運用メモです。
共通ルールは dotfiles の `templates/AGENTS_BASE.md` に集約します。

## Goal
- このプロジェクトは、物品貸し出しをバーコードで行うシステムの開発と改良を目的とする。

## Context
- 運用時に使用するパソコンはwindowsを想定している。場合によってはタブレットへの以降も考慮するが、ハードの故障や更新時に、詳しくない人が移行作業を行う可能性を考慮して、windowsスタンドアローンアプリとしての運用が前提となりそうだ。
- 貸し出しと返却に関しては基本的にバーコードリーダーの操作のみで完結させたいが、実装や運用上でミスが起こりそうなら無理には他のHUIを排除しない。(自作キーボード等の使用も可能)
- 使用するバーコードリーダーはLS2208の予定。動作としては数字入力とその後のenterの入力を確認したが、他の動作に関してはまだ具体的な仕様を確認していない。
- LS2208の商品情報はここ[https://www.zebra.com/us/en/support-downloads/scanners/general-purpose-scanners/ls2208.html]
- 使用するデータベースはSQLite。
- 簡易で良いので集計機能を実装する。csvでの出力ができるようにする。
- 物品の登録、検索、登録解除機能を実装する。
- 在庫状態リスト、貸し出し状態リスト、履歴は確認できるようにする。
- 使用時はGUIでの操作とする。
- 物品の登録はジャンル分け機能も実装する。
- 検証用スクリーンショットと、検証用ファイル、キャッシュの削除に関しては確認は不要。
- 同様の目的のasset内のファイルも確認なしで削除して良い。

## Commands
- `rtk python3 -m compileall src tests`: Python 構文チェック。
- `rtk python3 -m pytest -q`: テスト実行。事前に `python -m pip install -e ".[dev]"` が必要。
- `rtk python3 -m pittolog.main`: アプリ起動。事前に `python -m pip install -e .` が必要。
- `rtk python3 -m nuitka --mode=standalone --enable-plugin=pyside6 src/pittolog/main.py`: Windows 配布候補のビルド検証。実際には Windows 環境で確認する。

## Conventions
- GUI は PySide6 を使用する。
- DB は SQLite を使用し、標準ライブラリ `sqlite3` で扱う。
- バーコード値は `ITEM:*`, `DEPT:*`, `ACTION:*` の接頭辞で種別を判定する。
- 登録解除は物理削除ではなく `active = 0` で扱う。
- 小規模スタンドアローン運用を前提にし、ユーザー権限管理、同期、クラウド保存は実装しない。

## Risks
- LS2208 はキーボード入力として扱うため、読み取り欄のフォーカスが外れると入力を取り逃がす可能性がある。
- PySide6 は配布サイズが大きくなりやすい。Windows 配布時に Nuitka と PyInstaller を比較する。
- SQLite は複数端末同時利用には向かない。このプロジェクトでは対象外。

## Open Questions
- Windows 環境での最終配布方式は Nuitka / PyInstaller を実測比較して決める。
- バーコード PNG の実運用サイズは、印刷後に LS2208 で読み取りテストして調整する。
