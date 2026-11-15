# AEO Check

![AEO Checkの操作デモ：URL入力から技術診断、スコアと優先順位つき改善案の確認まで](docs/hero.gif)

<p align="center"><sub>サンプルHTMLを使用した操作デモ。実際のアプリ画面と診断ロジックで生成しています。</sub></p>

URLから、AI検索に向けたページの技術設定を診断するMVP。Python 3.12以上の標準ライブラリだけで動作します。APIキー不要。

```bash
python3 app.py
# http://127.0.0.1:8000
```

## 診断内容

- title、meta description、H1、H2、本文の取得可否
- JSON-LDのJSON構文、canonical、html lang
- meta robots / X-Robots-Tagのnoindex
- robots.txtによるOAI-SearchBot / ChatGPT-User / PerplexityBot / Googlebot / GPTBotの指定URLへのアクセス可否
- 優先順位つき改善案、JSONレポートの保存

スコアは9項目の独自の重みづけ合計（100点）。本文・構造化データ・インデックス設定は各15点、言語は5点、その他は各10点。ボットの許可設定はスコアに含みません。GPTBotは学習用として区別します。

**AI検索での引用率・実際の掲載状況を測定、保証するものではありません。** JavaScriptは実行しません。本文にはナビゲーション等が含まれ得ます。JSON-LDはスキーマ型や必須プロパティまで検証しません。robots.txtの取得失敗は不明として表示し、404/410はルールなしとして扱います。robots.txtは技術的なアクセス許可やHTTPステータスを保証しません。

## API

```bash
curl -X POST http://127.0.0.1:8000/api/audit \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com"}'
```

HTTP/HTTPSの標準ポートのみ対応。公開IPのみ許可し、各リダイレクト先も再検証します。検証済みIPへ接続を固定し、HTTPSの証明書は元のホスト名で検証します。レスポンス上限2MB、最大5回の転送、接続タイムアウト8秒。DNSの待ち時間はOSに依存します。直接接続のため、HTTPプロキシ必須の環境では取得できません。

## テスト

```bash
python3 -m unittest discover -s tests -v
node --check static/app.js
```

## 運用範囲

ローカル利用向けの開発サーバーです。履歴・認証・課金・定期実行は含みません。インターネットへ公開する際は、リバースプロキシ、認証、レート制限、リクエストの同時実行制限を追加してください。Google Fontsを使用し、読み込めない場合はシステムフォントへ切り替わります。

## READMEデモの再生成

開発用に `playwright` と `pillow` をインストールし、Chromiumが `/usr/bin/chromium` にある環境で実行します。アプリ本体にはこれらの依存は不要です。

```bash
python3 tools/create_hero.py
```

実際のUIを操作し、固定のサンプルHTMLを診断した結果から `docs/hero.gif` を生成します。外部サイトへのアクセスは行いません。
