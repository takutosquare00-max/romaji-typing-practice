# JLPT N5 ローマ字タイピング練習

日本語の読みをローマ字入力で練習するウェブアプリです。iPhone・タブレットでの利用を想定しています。

## 起動方法（ここが重要）

**開けない主な原因は「サーバーを違うフォルダで起動している」です。**  
必ず **`romaji-typing-practice` フォルダ内で** サーバーを起動してください。

### 方法1: 起動スクリプトを使う（推奨）

```bash
cd romaji-typing-practice
./start-server.sh
```

表示された **http://localhost:8765** をブラウザで開く。

### 方法2: 手動で起動

```bash
cd romaji-typing-practice
python3 -m http.server 8765
```

ブラウザで **http://localhost:8765** を開く（末尾のスラッシュや index.html は不要）。

### 開けないときの確認

| 現象 | 原因 | 対処 |
|------|------|------|
| 404 File not found | 別のフォルダでサーバーを起動している | 上記のとおり `romaji-typing-practice` に cd してから起動する |
| 一覧ページが出る | 同上（親フォルダで起動している） | アドレスを **http://localhost:8765** にし、`romaji-typing-practice` で起動し直す |
| 接続できない | サーバーが止まっている | ターミナルで `python3 -m http.server 8765` を実行し、止めずにブラウザで開く |

## 使い方

1. 上記のURLでページを開く（または `index.html` を直接開く）
2. 表示された日本語の文を、ローマ字で入力
3. 「チェック」ボタンまたは Enter で答え合わせ
4. 助詞の表記ゆれ（は→wa/ha、を→wo/o、へ→e/he）は自動で許容

## データの更新

問題文は `n5-typing-practice.md` と N5 問題集の読解文から抽出しています。

```bash
cd romaji-typing-practice
python3 -m venv .venv
source .venv/bin/activate
pip install pykakasi
python extract_sentences.py
```

`sentences.json` を更新したあと、`index.html` 内の `<script type="application/json" id="sentences-json">` の内容を同じJSONで差し替えると、アプリの出題が更新されます。

## ファイル構成

- `index.html` - メインアプリ（問題データはHTML内に埋め込み済み。外部ファイル不要）
- `sentences.json` - 問題データ（extract_sentences.pyの出力・更新時に参照）
- `extract_sentences.py` - 問題集から文を抽出・ローマ字変換するスクリプト
- `start-server.sh` - ローカルサーバー起動スクリプト

## GitHub へのデプロイ

### オプションA: 単独リポジトリとして公開

1. GitHubで新規リポジトリを作成（例: `romaji-typing-practice`）
2. 以下を実行:

```bash
cd romaji-typing-practice
git init
git add .
git commit -m "Initial commit: JLPT N5 ローマ字タイピング練習"
git branch -M main
git remote add origin https://github.com/<ユーザー名>/romaji-typing-practice.git
git push -u origin main
```

### オプションB: GitHub Pages で公開（無料でWeb公開）

1. 上記でリポジトリを作成・プッシュ
2. リポジトリの **Settings** → **Pages**
3. Source: **Deploy from a branch**
4. Branch: **main**、Folder: **/ (root)**
5. Save 後、数分で `https://<ユーザー名>.github.io/romaji-typing-practice/` で公開される

※ `index.html` がルートにあるため、そのまま静的サイトとして動作します。
