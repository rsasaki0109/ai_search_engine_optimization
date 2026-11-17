# lidar_slam_ros2：診断から公開後の再診断まで

対象: [lidar_slam_ros2](https://github.com/rsasaki0109/lidar_slam_ros2) · [改善PR #616](https://github.com/rsasaki0109/lidar_slam_ros2/pull/616)

公開後の確認日時（日本時間）: 2026-11-17T20:50:59.041317+09:00

## 改善内容

- READMEの既存の製品説明を画像より前へ移し、用途と導入文書への入口を先に提示。
- トップの重複したtitleを修正し、各ページ固有のtitle・descriptionを設定。
- canonical・ページ名・概要・言語と対応するWebPage / WebSiteのJSON-LDを追加。
- 日本語ページのJSON-LDをjaとして出力。
- PR時と公開時にMkDocsの厳格ビルド・4ページのメタデータ検証を実行。リリース用配布物にもテンプレートと検証スクリプトを収録。

## 公開後の実測

| ページ | 改善前 | 公開後 | 改善前の測定対象 |
| --- | ---: | ---: | --- |
| [index.html](https://rsasaki0109.github.io/lidar_slam_ros2/index.html) | 85 | 100 | 公開HTML |
| [getting-started.html](https://rsasaki0109.github.io/lidar_slam_ros2/getting-started.html) | 85 | 100 | 公開HTML |
| [getting-started-ja.html](https://rsasaki0109.github.io/lidar_slam_ros2/getting-started-ja.html) | 85 | 100 | 修正前ソースのローカルビルド |
| [comparison.html](https://rsasaki0109.github.io/lidar_slam_ros2/comparison.html) | 85 | 100 | 公開HTML |

AEO Checkの判定基準バージョン2、9項目の独自技術チェックによる値です。15点の増加はJSON-LDの有無と基本構造の判定によるものです。タイトルと概要の具体化は同じ点数項目の中の変更であり、加点理由には含めていません。AI検索での引用率、掲載状況、検索順位の改善を測定・保証する結果ではありません。

各ページはHTTPSで実取得して再診断しました。robots.txtは404/410として観測され、ルールなしとして表示されています。これを各ボットの実際のアクセス成功や引用の証拠としては扱いません。

## 公開反映の確認

マージコミット: `ee497c0993d259d21034409bb94f01713766f4ea`

[公開デプロイ識別情報](https://rsasaki0109.github.io/lidar_slam_ros2/docs-deployment-v1.json)を、既存の `check_public_docs_deployment.py` で検証しました。コミット番号・製品バージョン0.13.0・英語導入ページのHTMLハッシュとサイズ・source quickstartのアンカーと既存のfirst-map手順が一致し、結果はVERIFIEDでした。ハッシュ照合の対象は英語導入ページであり、全ページのバイト一致を個別に証明したものではありません。

詳細な値と検証結果は [JSON](lidar-slam-ros2.json) に保存しています。公開ページの内容は今後の更新で変わります。
