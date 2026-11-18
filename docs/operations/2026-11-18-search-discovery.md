# 実検索からの発見とリンク切れの観測（2026-11-18）

独自技術チェック100点の文書が、利用者の質問から見つかり、実際に読めるかを確認しました。今回の観測は利用可能なWeb検索ツールに各クエリを個別に送った単発の記録です。固定順位のSERP調査、一般利用者のテスト、AI回答内での引用測定ではありません。

## 検索結果で見つかったこと

| 入力したクエリ | 今回返された結果内での観測 |
| --- | --- |
| `LiDAR SLAM offline mapping without ROS 2 Python pip rosbag` | 自分のリポジトリ・DocsのURLは見つからず、第三者サービスのプロジェクト紹介が見つかった。ROSなしの利用を探す導線は引き続き課題 |
| `ROS 2 LiDAR SLAM Autoware compatible pointcloud map open source` | 旧名のGitHubリポジトリとリリースが見つかった。Autoware公式のSLAM一覧にもプロジェクトへの言及がある |
| `lidar_slam ROS 1 MCAP SQLite3 RKO-LIO` | 旧Docsのバイナリ互換性・配布ページが見つかった |
| `ROS 2 LiDAR SLAM accuracy comparison GLIM RKO-LIO` | 旧名のGitHubリポジトリと旧Docsのメディアページが見つかった |

[検索結果URLの記録](2026-11-18-search-discovery.json)には、一次情報と第三者サイトを分けて保存しました。返された件数は検索順位・露出数を表しません。返されなかったURLが検索インデックスに存在しないとも断定できません。旧名の検索結果や第三者サイトには古い説明・異なる時点のベンチマーク情報が残っているため、最新の比較条件は一次資料で確認する必要があります。

## 優先した改善：検索から入る旧Docsが404

リポジトリ改名後も旧DocsのURLが検索結果に残っています。GitHubリポジトリの改名による転送と、GitHub PagesのURLは別々に確認する必要があります。

[HTTP確認記録](2026-11-18-search-landings.json)では、旧 `/lidar_slam_ros2/readme-media.html` と `/lidar_slam_ros2/getting-started.html` が404、新 `/lidar_slam/readme-media.html` と新サイトマップが200でした。旧ページ全部の状態を網羅した記録ではありません。

ユーザーサイト側に旧パスの静的互換ページを生成する[復旧PR #1](https://github.com/rsasaki0109/rsasaki0109.github.io/pull/1)を作成しました。13ページを同名の新Docsへ案内します。GitHubの旧リポジトリ名は作り直しません。

- 各ページは新URLのcanonicalと通常リンクを持ち、JavaScript有効時はクエリ・フラグメントを保持して移動する。
- JavaScript無効時はmeta refreshと通常リンクで新URLへ案内する。この場合クエリ・フラグメントの保持は対象外。
- 単体テスト2件とChromiumでトップ階層・下位階層、JavaScript有効・無効の4経路を確認した。
- [新転送先13件](2026-11-18-new-doc-routes.json)は公開URLでHTTP 200を確認した。
- PRの[自動テスト](https://github.com/rsasaki0109/rsasaki0109.github.io/actions/runs/44212379785)は成功。公開前のPRであり、旧URLの公開復旧はまだ確認していない。

静的HTMLの案内であり、HTTP 301の実装ではありません。検索エンジンによる移行・順位の変化を保証するものでもありません。マージ・Pages公開後に旧URLが実際に200となり、新Docsへ到達することを再確認します。

## 次回と比較する項目

1. 旧URLから新Docsへ実際に到達できるか。
2. 同じ4クエリで、現行リポジトリや現行Docsが返されるか。実行日とURLを残す。
3. ROSなし利用の質問に対し、導入条件・対応入力・制約を一次資料から説明できるか。

今回は検索導線の不具合を見つけた観測です。構造化データ追加やFAQ改善による検索効果、AIからの引用率の変化は測定していません。
