# DB スキーマ

SQLite を使用します。

- `categories`: 物品カテゴリ
- `items`: 物品。登録解除は削除ではなく `active = 0` とし、`barcode = NULL` にする
- `departments`: 貸出先部署。登録解除は削除ではなく `active = 0` とし、`barcode = NULL` にする
- `loans`: 貸出状態。`returned_at IS NULL` が貸出中
- `events`: 貸出・返却の履歴

同じ物品が同時に複数部署へ貸し出されないように、`loans(item_id)` に `returned_at IS NULL` 条件付きの unique index を置きます。

バーコードは DB 内部の `id` とは別物です。貸出や履歴の紐付けは `id` で行い、バーコードは現場で読み取るための入力値として扱います。

有効な物品・部署のバーコードだけ一意にします。登録解除済みの行は `barcode = NULL` になるため、必要なら同じバーコードを手動指定で再利用できます。

自動採番は、現時点でDBに存在している非NULLバーコードの最大値 + 1 を使います。
