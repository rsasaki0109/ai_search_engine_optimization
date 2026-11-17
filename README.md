# AEO Check

**[GitHub Pages版](https://rsasaki0109.github.io/ai_search_engine_optimization/)** · 保存HTMLを端末内で診断（Pages有効化後に利用可能）

[![CI](https://github.com/rsasaki0109/ai_search_engine_optimization/actions/workflows/ci.yml/badge.svg)](https://github.com/rsasaki0109/ai_search_engine_optimization/actions/workflows/ci.yml)

![AEO Checkの操作デモ：URL入力から技術診断、スコアと優先順位つき改善案の確認まで](docs/hero.gif)

<p align="center"><sub>サンプルHTMLを使用した操作デモ。実際のアプリ画面と診断ロジックで生成しています。</sub></p>

URLから、AI検索に向けたページの技術設定を診断するMVP。Python 3.12以上の標準ライブラリだけで動作します。APIキー不要。

```bash
python3 app.py
# http://127.0.0.1:8000
```

## GitHub Pages（github.io）で使う

Renderの接続なしで使える静的配信版を追加しました。保存したUTF-8のHTML（2MBまで）と元のURLを指定すると、既存と同じPython解析ロジックをブラウザ内のPyodide 0.27.7で実行します。robots.txtは任意で指定できます（500KiBまで）。ファイルはサーバーへ送信せず、HTML内のJavaScriptも実行しません。履歴・前回比較・修正コード・JSON/Markdown・印刷/PDF・バックアップを利用できます。

GitHub PagesではPythonサーバーを動かせないため、URLからの自動取得・URL一括取得・サイトマップの取得は行いません。HTTPヘッダーも確認できないため、インデックス設定はHTML内だけの判定です。判定基準に `-html-file` を付け、サーバー取得版の履歴とはスコア比較しません。robots.txt未指定時のボット判定は不明として表示します。サンプル比較はPython実行環境の準備なしで利用できます。

最初の実ファイル診断時には、固定バージョンのPython実行環境をjsDelivr CDNから読み込みます。インターネット接続が必要で、初回は読み込み時間がかかります。ファイルの解析はWeb Worker内で行い、長時間応答がない場合はタイムアウトを表示します。画像・外部スクリプト・リンク先の内容は読み込みません。

### 公開設定（リポジトリ所有者の初回操作）

1. [Settings → Pages](https://github.com/rsasaki0109/ai_search_engine_optimization/settings/pages) を開く。
2. Build and deployment の Source を **GitHub Actions** に設定。
3. [GitHub Pagesワークフロー](https://github.com/rsasaki0109/ai_search_engine_optimization/actions/workflows/pages.yml)を **Run workflow** で実行。

以後はmainへのpushでビルド・公開します。公開先は https://rsasaki0109.github.io/ai_search_engine_optimization/ です。現在の連携ではPages設定の作成APIが403になるため、初回有効化だけは所有者の操作が必要です。未有効化時もビルド成果物を保存し、公開ジョブは実行しません。

```bash
python3 tools/build_pages.py
python3 -m http.server 8000 --directory dist-pages
# http://127.0.0.1:8000/
```

`tools/build_pages.py` はPythonの純粋な解析関数をASTから抽出し、サンプル結果・既存UIと一緒に `dist-pages/` を生成します。診断ロジックをJavaScriptへ二重実装していません。動作検証は `python3 tests/browser_pages.py` でプロジェクト用サブパス配信を再現します。

## URLなしで試す

トップの「URLなしでサンプルを試す」から、検証用ページの診断を体験できます。「① 修正前を見る」→「② 修正後と比較する」で、同じ診断ロジックによる30点→100点（+70点）の変化と、改善した6項目を表示します。本文・見出し・description・canonical・JSON-LDを整えた例です。

サンプルは外部サイトを取得せず、同梱HTMLを解析します。通常の履歴には保存せず、既存の履歴も変更しません。JSON・Markdown・印刷レポートには検証用サンプルである旨を含めます。100点はこのツールの技術チェックをすべて通過したという意味で、AI検索での掲載・引用や改善効果を保証しません。

サンプルHTMLは `static/demo/before.html` と `static/demo/after.html`、表示ページは `/demo/before` と `/demo/after` です。`GET /api/demo` は `before` と `after` の診断結果を返します。ブラウザ検証は `python3 tests/browser_demo.py` で実行できます。

## 診断内容

- title、meta description、H1、H2、本文の取得可否
- JSON-LDの構文・Schema.orgのcontext・型の指定（@graph・配列にも対応）、canonical、html lang
- meta robots / X-Robots-Tagのnoindex
- robots.txtによるOAI-SearchBot / ChatGPT-User / PerplexityBot / Googlebot / GPTBotの指定URLへのアクセス可否
- 優先順位つき改善案、適用場所つきの修正例とコピーボタン、JSON・Markdownレポートの保存、印刷用レイアウトからのPDF保存
- ブラウザ内の診断履歴（直近10件）、同じURLの前回結果との比較
- 最大5ページの一括診断、スコア・要改善数の一覧、一部取得失敗時の結果保持

スコアは9項目の独自の重みづけ合計（100点）。本文・構造化データ・インデックス設定は各15点、言語は5点、その他は各10点。ボットの許可設定はスコアに含みません。GPTBotは学習用として区別します。

**AI検索での引用率・実際の掲載状況を測定、保証するものではありません。** JavaScriptは実行しません。本文にはナビゲーション等が含まれ得ます。JSON-LDは型名の実在や必須プロパティ、リッチリザルト適合まで検証しません。robots.txtの取得失敗は不明として表示し、404/410はルールなしとして扱います。robots.txtは技術的なアクセス許可やHTTPステータスを保証しません。

## サイトマップから候補を選ぶ

「サイトマップからURLを選ぶ」にXMLのURLを入力すると、同じホストのページ候補を最大100件表示します。最大5件を選び、一括診断の入力欄へ移せます。候補を読み込むだけではページの診断は開始しません。

`urlset` と `sitemapindex`（標準の名前空間付き・名前空間なし）に対応します。インデックスは子サイトマップを選んで開きます。自動で再帰巡回せず、gzip形式・相対URL・別ホストの候補には対応しません。画像用などの入れ子のlocは候補に含めません。重複とフラグメントを除去し、除外件数と100件上限による省略を表示します。

APIは `POST /api/sitemap` に `{"url":"https://example.com/sitemap.xml"}` を送信します。応答は `source`（転送後URL）・`kind`（pages/index）・`urls`・`skipped`・`truncated` です。取得は公開IP・転送先検証と2MB上限を既存の診断と共有します。XMLのDTD・実体宣言は拒否します。

## 複数ページの一括診断

「複数ページをまとめて診断」から、1行に1件ずつ最大5件のURLを入力します。1リクエストにつき最大3件を並行処理し、入力順にスコア・要改善数・取得失敗の理由を表示します。URLのフラグメントを取り除いた後の完全一致で重複を除外します。自動でサイト全体を巡回する機能ではありません。

一部の取得に失敗しても他のページの結果は残ります。平均スコアは成功したページだけを対象に計算し、全件失敗時は表示しません。成功した結果は完了日時順で通常の履歴に保存します。「詳細を見る」からページごとの改善案・前回比較・Markdown保存・印刷/PDFへ進めます。「一括JSON ↓」は入力URL・結果・失敗理由・日時・集計を保存します（成功結果の本文抜粋も含みます）。一覧自体はブラウザを再読み込みすると消えますが、成功したページの履歴は残ります。

## クローラー判定の根拠

robots.txtはボットごとのproduct tokenを大文字小文字を区別せずに選択し、同じボットの複数グループを統合します。専用グループがあればそちらを使い、ない場合に `User-agent: *` を使います。複数のルールが一致する場合はパスの最長一致を採用し、同じ長さではAllowを優先します。`*`（ワイルドカード）と末尾の `$`（末尾一致）に対応します。

パスは大文字小文字を区別し、クエリを含めて判定します。UTF-8のパスと非予約文字のpercentエンコードを正規化し、予約文字のpercentエンコードは保持します。空のルールは制限として扱わず、SitemapやCrawl-delayはアクセス可否の判定には使いません。解析上限は500KiBで、超過した場合は途中までの判定を出さず不明として表示します。

ボットごとに適用グループ・一致したルール・元の行番号・選択理由を表示し、JSON・Markdown・印刷レポートにも含めます。過去の履歴に根拠データがない場合は再診断してください。robots.txtのルール上の判定であり、各サービスの実際の取得成功・運用・引用を再現するものではありません。スコアの配点・判定基準バージョンは変更しません。

## 構造化データの基本確認

JSON-LDごとに検出した型と問題点を表示します。Schema.orgのcontext（HTTP/HTTPS）、インラインの `@vocab`・名前空間prefix、絶対URL形式の型、型の配列、`@graph`、入れ子のcontextの継承・リセットに対応します。JSON構文エラー、型の未検出、不正な型指定やgraphの形式を要確認として表示します。NaNなど標準JSONでない値も通過させません。

構造化データの項目は、JSON-LDを1つ以上検出し、すべてのブロックが基本確認を通過した場合だけ加点します。1つに問題があっても他のブロックの検出結果は表示します。独自・外部contextは取得・展開しないため、「要確認」は必ずしもJSON-LDが不正という意味ではありません。型名の実在・必須項目・リッチリザルト適合は公式検証ツールで確認してください。解析はブロックごとに深さ60・要素2000を上限とし、超過時は手動確認を案内します。

判定基準バージョンは `2` です。以前の履歴も表示できますが、判定基準が違う結果とのスコア比較は行いません。APIには `analysis_version` と `schema_details`（ブロック番号・型・問題点・基本確認の通過状態）を含め、Markdownと印刷レポートにも詳細を表示します。

## 履歴のバックアップと復元

「診断履歴のバックアップ・復元」から、履歴を `aeo-history-backup.json` に保存できます。別のブラウザでは「バックアップを読み込む」でそのファイルを選んでください。URL・診断日時・診断結果・本文の抜粋・修正例を含みます。ファイルの内容はブラウザ内で処理し、サーバーに送信しません。

読み込んだ履歴は既存の履歴と統合して日時順に並べ、最新10件を残します。古い履歴は上限を超えると残らないため、必要なら読み込み前にもバックアップを保存してください。同じ診断日時とURLの記録は既存の履歴を優先し、日時はタイムゾーン表記の違いを正規化、URLはフラグメントを無視して判定します。旧判定基準の履歴も復元できます。

上限は5MiB、形式バージョン1・最大10件の専用バックアップだけを受け付けます。単独診断や一括診断のJSONファイルは復元用ではありません。ファイル内に不正な日時や診断データがある場合は全体を拒否し、履歴を変更しません。ブラウザの保存領域が使えない場合は、復元した履歴をそのタブ内だけに保持して案内します。

## レポートの共有

診断結果の「Markdown ↓」で、診断日時・スコア・前回比較・優先順位つき改善案・修正コード・技術チェック・クローラー設定を `.md` ファイルに保存できます。「JSON ↓」では元の診断結果を保存します。

「印刷 / PDF」からブラウザの印刷画面を開き、保存先に「PDFに保存」を選択してください。印刷時は修正例をすべて展開し、フォームや履歴・操作ボタンを非表示にします。印刷終了後は修正例の開閉状態を元に戻します。保存済みの履歴から出力する場合は元の診断日時を表示します。

Markdownと印刷レポートには、他のURLの履歴と本文の抜粋を含めません。対象ページのURL・診断上の検出内容・修正例は含みます。ブラウザによって印刷時の改ページは異なります。

## 履歴と前回比較

成功した診断は、URL・日時・診断結果・本文の抜粋を含めてブラウザのlocalStorageに直近10件保存します。「結果を見る」は保存結果を表示し、「再診断」はページを取得し直します。履歴はサーバーに送信せず、同じブラウザ・同じオリジンだけで利用できます。「履歴をすべて削除」で消去できます。保存できない環境ではタブ内だけで保持し、その旨を表示します。診断に失敗した場合は保存しません。

同じ取得後URLの直前の履歴と、スコア差・通過に変わった項目・要対応に変わった項目を比較します。URLのフラグメントは無視し、クエリは区別します。判定基準・診断項目・配点のいずれかが異なる場合は比較しません。技術チェックの変化を示す機能で、AI検索の評価の変化を測るものではありません。

## 修正例の使い方

診断結果の「修正例と適用方法を見る」を開くと、HTMLの適用場所、確認事項、コピー可能なコードが表示されます。title・descriptionなどの【】内は実際の内容に置き換えてください。構造化データは取得したタイトルとURLを使った汎用WebPageのひな形です。canonicalは取得後のURLを候補にするため、クエリを含め正規URLを確認してください。

例はサイトへ自動適用しません。既存タグとの重複を避けて統合してください。noindexは公開意図やHTTPヘッダーの確認が必要なため、コピー用コードを表示せず手動の確認手順を案内します。クリップボードへの書き込みが拒否された場合は、コードを選択して手動コピーを案内します。

## API

```bash
curl -X POST http://127.0.0.1:8000/api/audit \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com"}'
```

一括診断は別のエンドポイントで受け付けます。

```bash
curl -X POST http://127.0.0.1:8000/api/audit/batch \
  -H 'Content-Type: application/json' \
  -d '{"urls":["https://example.com/","https://example.com/guide"]}'
```

`urls` は1〜5件の配列。形式の不正や上限超過はHTTP 400、個別の取得失敗はHTTP 200の `results` 各行に `error` として返します。成功した行は `report` を含み、各行に `url` と `at`（完了日時）があります。`summary` は `total`・`succeeded`・`failed`・`average_score`（成功なしならnull）を含みます。本文上限は単独診断4KiB、一括診断16KiBです。URLの公開IP検証・転送先の再検証は単独診断と共通です。

未通過のチェックには `repair`（`location`・`code`・`note`）を含みます。手動確認だけの項目では `code` は `null` です。通過したチェックには `repair` を含みません。

HTTP/HTTPSの標準ポートのみ対応。公開IPのみ許可し、各リダイレクト先も再検証します。検証済みIPへ接続を固定し、HTTPSの証明書は元のホスト名で検証します。レスポンス上限2MB、最大5回の転送、接続タイムアウト8秒。DNSの待ち時間はOSに依存します。環境のHTTP_PROXY / HTTPS_PROXY / NO_PROXYを利用できます。プロキシはhttp://形式のHTTP CONNECTに対応し、検証済みIPへトンネルを接続します。HTTPSのSNI・証明書検証とHostヘッダーには元のホスト名を使います。SOCKS・HTTPS形式のプロキシや、対象ポートへのCONNECTを許可しないプロキシでは取得できません。接続失敗時に別経路へ自動フォールバックしません。

## テスト

```bash
python3 -m unittest discover -s tests -v
node --check static/app.js
node --test tests/history.test.cjs tests/report.test.cjs
```

## 自動テスト（GitHub Actions）

push・PRでPython 3.12/3.13の単体テスト、Node.js 22のJavaScript構文・履歴・レポートテストを実行します。別ジョブでChromiumによる履歴・比較・一括診断・Markdown保存・PDF生成を検証します。診断対象は固定HTMLのテストデータを使用し、外部サイトやAPIキーに依存しません。

ブラウザ検証をローカルでも実行する場合：

```bash
python3 -m pip install -r requirements-browser.txt
python3 -m playwright install --with-deps chromium
CHROMIUM_EXECUTABLE= python3 tests/browser_history.py
CHROMIUM_EXECUTABLE= python3 tests/browser_report.py
CHROMIUM_EXECUTABLE= python3 tests/browser_batch.py
```

PDF検証には `pdftotext`（Ubuntuでは `poppler-utils`）が必要です。日本語表示にはNoto CJKなどの日本語フォントを使用してください。`CHROMIUM_EXECUTABLE` を指定しない場合は `/usr/bin/chromium`、空文字の場合はPlaywright付属のChromiumを使います。これらの開発用依存はアプリの起動には不要です。

## 運用範囲

単一インスタンス向けの公開β版です。履歴はブラウザ内だけに保存します。サーバー上の履歴保存・アカウント同期・認証・課金・定期実行は含みません。HTTPS終端はホスティング側で行ってください。プロセス全体の利用上限と同時処理制限を設けています。認証や複数インスタンス間の共有制限は含みません。Google Fontsを使用し、読み込めない場合はシステムフォントへ切り替わります。

## READMEデモの再生成

開発用に `playwright` と `pillow` をインストールし、Chromiumが `/usr/bin/chromium` にある環境で実行します。アプリ本体にはこれらの依存は不要です。

```bash
python3 tools/create_hero.py
```

実際のUIを操作し、固定のサンプルHTMLを診断した結果から `docs/hero.gif` を生成します。外部サイトへのアクセスは行いません。

履歴のブラウザ検証（同じ開発用依存を使用）：

```bash
python3 tests/browser_history.py
```

レポートのブラウザ検証（同じ開発用依存と `pdftotext` を使用）：

```bash
python3 tests/browser_report.py
```

一括診断のブラウザ検証（同じ開発用依存を使用）：

```bash
python3 tests/browser_batch.py
```

## 公開サイトでの検証

[実測記録](docs/public-site-validation.md)と[JSON](docs/public-site-validation.json)を保存しています。手動で再検証する場合は `python3 tools/validate_public_sites.py` を実行してください。10サイトのHTTPSページと追加のHTTP経路を対象に、ページとrobots.txtを取得します。外部への通信を伴うためCIでは実行しません。スコアは掲載・引用の評価ではなく、取得時点の独自技術チェック指標です。

## 公開β版の運用制限とデプロイ

標準設定は、プロセス全体で毎分30URL（サイトマップ取得は1件、一括診断は入力件数分）・同時診断3件・受信接続16件です。IP単位の制限ではなく、利用者全体で共有する枠です。再起動で利用枠がリセットされるため、単一インスタンスの小規模β版を対象にします。サンプル診断とヘルスチェックはURL取得枠を消費しません。制限超過時は429、処理枠が埋まった場合は503で再試行を案内します。一括診断では個別の混雑エラーを各結果に含めます。

入力本文は単独診断・サイトマップ4KiB、一括診断16KiBまで。受信ソケットは10秒のタイムアウトを設定し、同一サイト以外のOriginを持つPOSTは拒否します。サーバーのDNS待ち時間はOSに依存し、1つの枠が長時間使われる可能性は残ります。大規模な攻撃対策や複数インスタンス化には、外部のレート制限・WAF・ジョブキューが必要です。

```bash
docker build -t aeo-check .
docker run --rm -p 8000:8000 aeo-check
# http://127.0.0.1:8000
```

コンテナはUID 10001で起動し、`HOST`・`PORT` を環境変数から読みます。`GET /healthz` は外部取得なしで状態を返します。Render用の `render.yaml` は無料プラン・1インスタンス・ヘルスチェック・CI成功後の自動デプロイを指定しています。無料枠の稼働・休止条件や提供可否はRender側の現行条件に従います。

[RenderでBlueprintを作成](https://dashboard.render.com/blueprint/new?repo=https://github.com/rsasaki0109/ai_search_engine_optimization)して、GitHubリポジトリへのアクセスを承認するとデプロイ設定を読み込めます。公開URLの発行はRenderアカウントとの接続・デプロイ成功後です。リポジトリに秘密情報を保存する必要はありません。公開後は `/healthz`、サンプル比較、実サイト1件、一括診断、429時の案内を確認してください。

CIでは単体テスト・HTTP制限の統合テスト・ブラウザ検証に加え、Dockerイメージをビルドし、ヘルスチェックとサンプル診断をコンテナ内で実行します。

## 自分のOSSでの改善事例

[lidar_slam_ros2の診断・修正・公開後再診断](docs/case-studies/lidar-slam-ros2.md)を記録しました。4ページの独自技術チェックは85→100点。JSON-LD追加による判定上の変化であり、AI検索の引用率や掲載効果を測定した値ではありません。
