# LINE設定手順

## 1. LINE Developersアカウント作成

1. [LINE Developers](https://developers.line.biz/) にアクセス
2. LINEアカウントでログイン → プロバイダーを作成

## 2. Messaging API チャンネル作成

1. プロバイダー → 新しいチャンネル → Messaging API
2. チャンネル情報を入力（店舗名など）
3. チャンネル基本設定 → チャンネルシークレットを確認
4. Messaging API設定 → チャンネルアクセストークン → 発行

取得した情報を環境変数に設定:
```
LINE_CHANNEL_ACCESS_TOKEN=xxxx
LINE_CHANNEL_SECRET=xxxx
```

## 3. Webhook設定

Messaging API設定 → Webhook URL:
```
https://your-app.onrender.com/api/v1/webhook/line/84a402b7-ba98-4f71-83da-5452247b835b
```

※ `{store_id}` はDBに登録した店舗のUUID

- Webhookの利用: オン
- 検証ボタンで疎通確認

## 4. LIFFアプリ作成

1. LINE Developers → LINEログイン チャンネルを作成（なければ）
2. LIFF → LIFFアプリを追加

| 設定 | 値 |
|---|---|
| LIFFアプリ名 | 予約 |
| サイズ | Full |
| エンドポイントURL | `https://your-app.onrender.com/liff/booking.html` |
| Scope | profile, openid |
| ボットリンク機能 | On（Aggressive） |

LIFFアプリのIDをメモ → `LINE_LIFF_ID=2009586205-CyS3JZM7`

## 5. リッチメニュー設定

LINE Official Account Manager でリッチメニューを作成:

| エリア | テキスト | アクション |
|---|---|---|
| 大ボタン | ご予約 | URI: `https://liff.line.me/{LIFF_ID}?store_id={store_id}&action=book` |
| 中ボタン | 予約確認 | URI: `https://liff.line.me/{LIFF_ID}?store_id={store_id}&page=my-reservations` |

## 6. LIFFページのLIFF_ID設定

`frontend/liff/booking.html` と `frontend/liff/my-reservations.html` の以下を変更:

```javascript
window.LIFF_ID = "1234567890-xxxxxxxx";  // あなたのLIFF_ID
```

## 店舗ごとのLINE設定（複数店舗）

店舗ごとに異なるLINEチャンネルを使う場合は、管理画面の設定画面からLINE設定を入力します。
DBの `stores.line_channel_id`, `stores.line_channel_secret`, `stores.line_access_token` に保存されます。

設定がない場合は環境変数のデフォルト値を使用します。
