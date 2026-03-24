# Renderデプロイ手順

## 現在の設定値（ローカル開発環境）

| 項目 | 値 |
|---|---|
| GitHubリポジトリ | https://github.com/Nakamura0902/linebook |
| ストアID | `84a402b7-ba98-4f71-83da-5452247b835b` |
| 管理者ログイン | admin@example.com / password123 |
| LINE Channel Secret | `ab23ccddbcfc223799e93dc1d3a9c805` |
| LINE Access Token | `.env` 参照 |
| LIFF ID | `2009586205-CyS3JZM7` |
| ngrok URL（一時） | `https://toilful-stellularly-eugenio.ngrok-free.dev` |

**ローカルURL一覧:**
- 管理画面: http://localhost:8000/admin/
- API docs: http://localhost:8000/docs
- Webhook: http://localhost:8000/api/v1/webhook/line/84a402b7-ba98-4f71-83da-5452247b835b
- 予約LIFF: https://liff.line.me/2009586205-CyS3JZM7?store_id=84a402b7-ba98-4f71-83da-5452247b835b&action=book
- 予約確認LIFF: https://liff.line.me/2009586205-CyS3JZM7?store_id=84a402b7-ba98-4f71-83da-5452247b835b&page=my-reservations

---

## Renderへの本番デプロイ手順

### 1. PostgreSQLデータベース作成

Render Dashboard → New → PostgreSQL

| 設定 | 値 |
|---|---|
| Name | linebook-db |
| Database | linebook |
| Region | Singapore |
| Plan | Free（初期） |

作成後、**Internal Database URL** をメモ（次のステップで使用）。

### 2. Webサービス作成

Render Dashboard → New → Web Service → `Nakamura0902/linebook` を選択

| 設定 | 値 |
|---|---|
| Name | linebook-api |
| Region | Singapore |
| Branch | main |
| Runtime | Python 3 |
| Build Command | `cd backend && pip install -r requirements.txt && pip install eval_type_backport && alembic upgrade head` |
| Start Command | `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

### 3. 環境変数設定

Render Dashboard → linebook-api → Environment に以下を追加:

```
APP_ENV=production
DATABASE_URL=（Step 1のInternal Database URL）
JWT_SECRET_KEY=31caaddd4fbd8c26373b7cc721a867757f6233414732776e164da238edb8fc8b
APP_SECRET_KEY=32af8fe66ca37b44dd49496544ee26a20115ea5e54d62c9f82f47366db15388f
LINE_CHANNEL_ACCESS_TOKEN=（.envのLINE_CHANNEL_ACCESS_TOKEN）
LINE_CHANNEL_SECRET=ab23ccddbcfc223799e93dc1d3a9c805
LINE_LIFF_ID=2009586205-CyS3JZM7
GOOGLE_CLIENT_ID=（Google Cloud Consoleから）
GOOGLE_CLIENT_SECRET=（Google Cloud Consoleから）
GOOGLE_REDIRECT_URI=https://linebook-api.onrender.com/api/v1/admin/google/callback
CORS_ORIGINS=https://linebook-api.onrender.com
```

### 4. 初期データ投入

デプロイ後、Render Shell から:

```bash
cd backend && python seed.py
```

### 5. LINE Webhook URLの更新

デプロイ後、LINE DevelopersコンソールのWebhook URLを更新:
```
https://linebook-api.onrender.com/api/v1/webhook/line/84a402b7-ba98-4f71-83da-5452247b835b
```

### 6. LIFF エンドポイントURLの更新

LINE Developers → LIFFアプリのエンドポイントURLを更新:
```
https://linebook-api.onrender.com/liff/booking.html
```

### 7. 動作確認

```
https://linebook-api.onrender.com/admin/      → 管理画面ログイン
https://linebook-api.onrender.com/docs        → API ドキュメント
```

---

## ローカル開発環境の起動

```bash
cd backend

# 依存パッケージインストール
pip install -r requirements.txt
pip install eval_type_backport bcrypt==4.0.1

# 初期データ投入
python seed.py

# 起動
uvicorn app.main:app --reload --port 8000
```

ngrok（LINE Webhook用）:
```bash
ngrok http 8000
# → 取得したURLをLINE DevelopersのWebhook URLに設定
```

## テスト実行

```bash
cd backend
pytest tests/ -v
```

## 注意事項

- Renderのフリープランはスリープあり（15分無操作でスリープ）
- スリープ後の初回リクエストは30秒程度かかる
- 本番運用は Starter Plan以上を推奨
- SQLiteは本番で使用しないこと（Renderのファイルシステムは揮発性）
- `eval_type_backport` は Python 3.8 での Pydantic v2 動作に必要
- `bcrypt==4.0.1` を使用すること（5.x は passlib 1.7.4 と非互換）
