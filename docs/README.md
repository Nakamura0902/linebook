# LINE予約SaaS (line-book)

LINEを起点に予約が完結するSaaS型予約システム。初期ターゲットは美容室。将来的に飲食店・個人塾・クリニックへ拡張可能な構造。

## 機能概要

| 機能 | 説明 |
|---|---|
| LINE/LIFF予約 | LINEリッチメニュー → LIFF画面で予約完結 |
| 管理画面 | 予約一覧・カレンダー・顧客・スタッフ・メニュー管理 |
| 通知 | 予約完了・変更・取消・前日リマインド（LINE） |
| Googleカレンダー連携 | 予約を自動書き込み・外部更新の受信 |
| マルチテナント | 企業→店舗構造。複数店舗対応 |
| ダブルブッキング防止 | DB制約 + アプリロジックの多層防止 |
| CSV出力 | 顧客一覧・予約一覧 |
| 代理登録 | 電話予約を管理者が手動登録 |

## 技術スタック

| 区分 | 技術 |
|---|---|
| Backend | Python 3.11 / FastAPI / SQLAlchemy |
| Database | PostgreSQL（開発: SQLite） |
| Frontend | HTML / CSS / Vanilla JavaScript |
| LIFF | LINE Front-end Framework |
| 通知 | LINE Messaging API |
| カレンダー | Google Calendar API |
| デプロイ | Render |
| スケジューラ | APScheduler |

## ディレクトリ構成

```
line-book/
├── backend/               # FastAPI バックエンド
│   ├── app/
│   │   ├── main.py        # エントリポイント
│   │   ├── models/        # SQLAlchemyモデル
│   │   ├── routers/       # APIルーター
│   │   │   ├── admin/     # 管理者API
│   │   │   ├── liff/      # LIFF API
│   │   │   └── webhook.py # LINE/Google Webhook
│   │   ├── services/      # ビジネスロジック
│   │   ├── industry/      # 業種別テンプレート
│   │   ├── schemas/       # Pydanticスキーマ
│   │   └── core/          # 認証・セキュリティ・ログ
│   ├── alembic/           # DBマイグレーション
│   ├── tests/             # テスト
│   ├── seed.py            # 初期データ投入
│   └── requirements.txt
├── frontend/
│   ├── admin/             # 管理画面（HTML/CSS/JS）
│   ├── liff/              # LIFF予約画面
│   └── shared/            # 共通CSS/JS
├── docs/                  # ドキュメント
└── render.yaml            # Renderデプロイ設定
```

## クイックスタート

```bash
# 1. リポジトリのクローン
cd line-book

# 2. 環境変数設定
cp backend/.env.example backend/.env
# .envを編集

# 3. 依存パッケージインストール
cd backend
pip install -r requirements.txt

# 4. データベース初期化（SQLite開発用）
python seed.py

# 5. 起動
uvicorn app.main:app --reload
```

管理画面: http://localhost:8000/admin/
API Docs: http://localhost:8000/api/docs

ログイン情報（seedデータ）:
- メール: admin@example.com
- パスワード: password123
