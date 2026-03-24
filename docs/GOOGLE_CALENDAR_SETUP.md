# Googleカレンダー設定手順

## 1. Google Cloud Projectの作成

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 新しいプロジェクトを作成（例: linebook）

## 2. Google Calendar APIの有効化

1. APIとサービス → ライブラリ
2. "Google Calendar API" を検索 → 有効にする

## 3. OAuth2認証情報の作成

1. APIとサービス → 認証情報 → 認証情報を作成 → OAuthクライアントID
2. アプリケーションの種類: ウェブアプリケーション
3. 承認済みのリダイレクトURI に追加:
   ```
   https://your-app.onrender.com/api/v1/admin/google/callback
   http://localhost:8000/api/v1/admin/google/callback  (開発用)
   ```
4. クライアントIDとシークレットをメモ

環境変数に設定:
```
GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxxx
GOOGLE_REDIRECT_URI=https://your-app.onrender.com/api/v1/admin/google/callback
```

## 4. 管理画面からの連携設定

1. 管理画面 → 設定 → Googleカレンダー
2. 「Google連携を設定する」ボタンをクリック
3. Googleアカウントでログイン → カレンダーアクセスを許可
4. コールバック後、store.google_refresh_token にトークンが保存される

## 5. 連携の仕組み

### 予約 → Googleカレンダー（書き込み）

予約確定時にバックグラウンドタスクとして実行:
- 予約をGoogleカレンダーイベントとして作成
- `extendedProperties.private.linebook_reservation_id` に予約IDを記録
- 失敗してもDB側の予約は確定状態を維持（ベストエフォート）

### Googleカレンダー → 予約枠ブロック（読み取り）

Gcal Push通知 (Webhook) で受信:
1. `POST /webhook/google/{store_id}` にGcal変更通知が届く
2. DBに存在しない外部イベントを `reservation_blocks` として登録
3. 空き枠計算時にブロックが考慮される

### Webhook有効期限の更新

GcalのWebhookは最大7日間有効。APSchedulerで週1回自動更新:
```python
# services/google_calendar_service.py の setup_webhook を定期実行
```

## 6. カレンダー構造

| カレンダー | 用途 |
|---|---|
| 店舗カレンダー | `stores.google_calendar_id` で設定。予約を書き込む先 |
| スタッフカレンダー | `staff.google_calendar_id` で設定。将来: スタッフ個人予定との連携 |

## 注意事項

- リフレッシュトークンは `stores.google_refresh_token` に保存される（将来の暗号化対応を推奨）
- Google OAuth同意画面は「内部」（組織内のみ）または「外部」（要審査）を選択
- 開発時は「テストユーザー」にGoogleアカウントを追加して動作確認
