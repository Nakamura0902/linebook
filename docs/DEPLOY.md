# Renderデプロイ手順

## 事前準備

1. [Render](https://render.com) にアカウント作成・ログイン
2. GitHubリポジトリにコードをプッシュ
3. LINE Developers設定完了（LINE_SETUP.md 参照）

## デプロイ手順

### 1. PostgreSQLデータベース作成

Render Dashboard → New → PostgreSQL

| 設定 | 値 |
|---|---|
| Name | linebook-db |
| Database | linebook |
| Region | Singapore |
| Plan | Free（初期） |

作成後、Internal Database URLをメモ。
postgresql://linebook_user:0PRodTYVIJOLimYWja5w4W8KwthegTdE@dpg-d714kjfgi27c73f681f0-a/linebook

### 2. Webサービス作成

Render Dashboard → New → Web Service → GitHubリポジトリを選択

| 設定 | 値 |
|---|---|
| Name | linebook-api |
| Region | Singapore |
| Branch | main |
| Runtime | Python 3 |
| Build Command | `cd backend && pip install -r requirements.txt && alembic upgrade head` |
| Start Command | `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |

### 3. 環境変数設定

Render Dashboard → linebook-api → Environment

必須の環境変数（ENV_VARS.md 参照）を設定:

```
APP_ENV=production
DATABASE_URL=（Step 1のInternal Database URL）
JWT_SECRET_KEY=（openssl rand -hex 32 で生成）
APP_SECRET_KEY=（openssl rand -hex 32 で生成）
LINE_CHANNEL_ACCESS_TOKEN=（LINE設定から）
LINE_CHANNEL_SECRET=（LINE設定から）
LINE_LIFF_ID=（LINE設定から）
GOOGLE_CLIENT_ID=（Google Cloud Consoleから）
GOOGLE_CLIENT_SECRET=（Google Cloud Consoleから）
GOOGLE_REDIRECT_URI=https://your-app.onrender.com/api/v1/admin/google/callback
CORS_ORIGINS=https://your-app.onrender.com
```

### 4. 初期データ投入

デプロイ後、Render Shell から:

```bash
cd backend && python seed.py
```

または render.yaml の buildCommand に追加:

```yaml
buildCommand: |
  cd backend
  pip install -r requirements.txt
  alembic upgrade head
  python seed.py
```

### 5. 動作確認

```
https://your-app.onrender.com/health      → {"status": "ok"}
https://your-app.onrender.com/admin/      → 管理画面ログイン
https://your-app.onrender.com/api/docs    → API ドキュメント（本番では非表示）
```

## render.yaml による自動デプロイ

リポジトリルートの `render.yaml` を使って Blueprint からデプロイも可能:

Render Dashboard → New → Blueprint → リポジトリを選択

## 注意事項

- Renderのフリープランはスリープあり（15分無操作でスリープ）
- スリープ後の初回リクエストは30秒程度かかる
- 本番運用は Starter Plan以上を推奨
- SQLiteは本番で使用しないこと（Renderのファイルシステムは揮発性）
- APScheduler（リマインダー）はWebサービスと同プロセスで動作
  - Renderの有料プランでは Cron Job サービスとして分離することを推奨

## ローカル開発環境の起動

```bash
cd backend

# 仮想環境作成（推奨）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存パッケージインストール
pip install -r requirements.txt

# .env作成
cp .env.example .env
# .envのDATABASE_URLをSQLiteに変更: sqlite:///./linebook.db

# 初期データ投入
python seed.py

# 起動
uvicorn app.main:app --reload --port 8000
```

## テスト実行

```bash
cd backend
pytest tests/ -v
```
