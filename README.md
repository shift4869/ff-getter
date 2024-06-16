# ff-getter

![Coverage reports](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/shift4869/ad61760f15c4a67a5c421cf479e3c7e7/raw/03_ff-getter.json)

## 概要
自分のツイッターアカウントに紐づくAPIトークンを通して、  
自分がフォローしているアカウント( `following` )と、  
自分をフォローしているアカウント( `follower` )を取得して、  
 `ff_list_{yyyymmdd}.txt` として書き出す。


## 特徴（できること）
- 概要の通り  
    - `following` / `follower` を取得して、 `ff_list_{yyyymmdd}.txt` として書き出す。  
    - 実行ファイルから見て `./result/` ディレクトリ以下に出力される。  
    - その際に `./result/` ディレクトリ内に前回実行時の結果ファイルが存在するならば、差分も出力に含める。  
    - configで指定できる `reserved_file_num` 個(デフォルトは10個)以上のファイル数があるならば、古い順に `./bak/` ディレクトリに移動させる。  


## 前提として必要なもの
- Pythonの実行環境(3.12以上)
- twitterのセッション情報
    - ブラウザでログイン済のアカウントについて、以下の値をクッキーから取得
        - ct0 (クッキー中)
        - auth_token (クッキー中)
        - target_screen_name(収集対象の@なしscreen_name)
        - target_id (クッキー中の"twid"の値について、"u%3D{target_id}"で表される数値列)
    - ブラウザ上でのクッキーの確認方法
        - 各ブラウザによって異なるが、概ね `F12を押す→ページ更新→アプリケーションタブ→クッキー` で確認可能
    - 詳しくは「twitter クッキー ct0 auth_token」等で検索


## 使い方
1. このリポジトリをDL
    - 右上の「Clone or download」->「Download ZIP」からDLして解凍  
1.  `./tests/config/` ディレクトリ内のすべてのファイルを `./config/` ディレクトリ内にコピー   
1.  `./config/dummy_*` それぞれのファイル名から `dummy_` を削除する   
1.  ファイルの中身を編集する   
    -  `dummy` が含まれる項目に自分のtwitterアカウントのセッション情報を設定する（必須）  
1. `main.py` を実行する
    ```
    python ./src/ff_getter/main.py
    ```
    有効なオプションは `python ./src/ff_getter/main.py -h` で確認できる  
    configファイルの設定よりオプションでの指定の方が優先される  
1. 出力された `./result/ff_list_{yyyymmdd}.txt` を確認する  


## License/Author
[MIT License](https://github.com/shift4869/FFGetter/blob/master/LICENSE)  
Copyright (c) 2022 - 2024 [shift](https://twitter.com/_shift4869)
