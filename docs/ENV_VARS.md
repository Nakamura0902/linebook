# 環境変数一覧

## 必須

| 変数名 | 説明 | 例 |
|---|---|---|
| `DATABASE_URL` | DB接続URL | `postgresql://user:pass@host:5432/linebook` |
| `JWT_SECRET_KEY` | JWT署名キー（32文字以上のランダム文字列） | `openssl rand -hex 32` で生成 |
| `APP_SECRET_KEY` | アプリシークレット | 同上 |

## LINE設定

| 変数名 | 説明 | 取得場所 |
|---|---|---|
| `LINE_CHANNEL_ACCESS_TOKEN` | Messaging APIのチャンネルアクセストークン | LINE Developersコンソール |
| `LINE_CHANNEL_SECRET` | チャンネルシークレット | LINE Developersコンソール |
| `LINE_LIFF_ID` | LIFFアプリのID | LINE Developersコンソール |

## Google Calendar設定

| 変数名 | 説明 | 取得場所 |
|---|---|---|
| `GOOGLE_CLIENT_ID` | OAuth2クライアントID | Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | OAuth2クライアントシークレット | Google Cloud Console |
| `GOOGLE_REDIRECT_URI` | OAuth2コールバックURL | 例: `https://your-app.onrender.com/api/v1/admin/google/callback` |

## アプリケーション設定

| 変数名 | デフォルト | 説明 |
|---|---|---|
| `APP_ENV` | `development` | `development` or `production` |
| `DEBUG` | `false` | SQLクエリログ出力 |
| `CORS_ORIGINS` | `http://localhost:3000` | CORS許可オリジン（カンマ区切り） |
| `LIFF_BASE_URL` | `` | LIFF URL（通知内リンク生成用） |
| `ADMIN_BASE_URL` | `` | 管理画面URL |
| `SCHEDULER_ENABLED` | `true` | 前日リマインドスケジューラ |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | アクセストークン有効期限（分） |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | リフレッシュトークン有効期限（日） |

## 開発時のみ使用

| 変数名 | 説明 |
|---|---|
| `DATABASE_URL=sqlite:///./linebook.db` | SQLite使用（開発用） |

## セキュリティ注意事項

- `JWT_SECRET_KEY` は本番環境では必ず変更すること（32文字以上の乱数推奨）
- `LINE_CHANNEL_SECRET` は絶対に外部公開しないこと
- `GOOGLE_CLIENT_SECRET` はOAuthフロー以外では使用しないこと
- Renderの環境変数設定は「Secret Files」または「Environment Groups」を利用推奨
