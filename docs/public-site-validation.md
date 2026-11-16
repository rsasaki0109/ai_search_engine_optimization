# 公開サイトの取得・診断検証

実行日時（UTC）: 2026-11-16T00:26:21.966152+00:00

公開10サイトのHTTPSページで、ページ取得・9項目の診断・5ボットのrobots.txt判定が完了しました。追加のHTTP接続1件は、この環境のプロキシ経路で切断されました。対象サイト側のアクセス拒否とは断定できません。

これは取得と診断処理の実測です。全判定の人手による正誤評価、各AI検索サービスでの引用確認、公開環境での負荷試験ではありません。スコアは対象サイトの品質やAI検索の掲載を評価するランキングではありません。

| URL | 結果 | ページ最終HTTP | robots.txt最終HTTP | 秒 |
| --- | --- | --- | --- | --- |
| https://example.com | 診断完了 | 200 | 404 | 5.26 |
| http://example.com | 接続失敗 | 未取得 | 未取得 | 1.03 |
| https://www.python.org/ | 診断完了 | 200 | 200 | 0.34 |
| https://www.sqlite.org/index.html | 診断完了 | 200 | 200 | 0.6 |
| https://developer.mozilla.org/en-US/ | 診断完了 | 200 | 200 | 0.37 |
| https://www.rfc-editor.org/rfc/rfc9309 | 診断完了 | 200 | 200 | 0.62 |
| https://www.w3.org/standards/ | 診断完了 | 200 | 200 | 0.48 |
| https://www.iana.org/domains/reserved | 診断完了 | 200 | 200 | 0.62 |
| https://www.wikipedia.org/ | 診断完了 | 200 | 200 | 0.49 |
| https://www.gnu.org/software/ | 診断完了 | 200 | 200 | 0.84 |
| https://www.rust-lang.org/ | 診断完了 | 200 | 404 | 0.94 |

## 観測と修正

- W3Cのページで値なしのHTML属性によりAttributeErrorが発生。属性値を空文字へ正規化し、回帰テストを追加。修正後は全10サイトで予期しない例外なし。
- 直接TCP接続を利用できない実行環境で取得できなかったため、環境のHTTP CONNECTプロキシに対応。各URLと転送先の公開IP検証・検証済みIPへの接続固定・元のホスト名でのTLS証明書検証を維持。
- RFC EditorとRustのページで転送先URLの診断を確認。Wikipediaではrobots.txtの別ホストへの転送を確認。
- example.comとRustのrobots.txtは最終HTTP 404。ルールなしとして扱う挙動を確認。
- 403・429などの実サイト拒否は今回は観測されず。拒否時のエラー・不明表示は固定応答のテストで確認する。

## 再現と制限

`python3 tools/validate_public_sites.py` で再実行できます。外部サイトを取得する手動検証であり、CIには含めません。詳細は [JSON](public-site-validation.json) を参照してください。

プロキシ経由では対象のIP・ポートへのCONNECTが必要です。この環境のHTTP（80番ポート）経路の切断は未解消であり、HTTPSページの成功をHTTPページ全般の成功と読み替えることはできません。gzip応答やJavaScript実行は検証対象外です。外部サイトの応答やネットワーク条件は時点により変わります。
