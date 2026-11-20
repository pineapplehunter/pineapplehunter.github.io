---
title: このサイトの作り方
date: 2026-11-20
summary: Markdown から静的ページを生成する流れと、Ninja が管理するビルド手順を紹介します。
---

このサイトは、Markdown ファイルをもとに作られています。各記事のタイトル、日付、概要は YAML フロントマターに書き、ファイル名の言語サフィックスより前の部分を URL に使います。

## Ninja が実行する処理

`./build.sh` は `configure.py` を呼び出して、記事などのファイルを探し、Ninja のビルドグラフを生成します。Ninja はページをレンダリングし、各ページの HTML に合わせて Tailwind CSS を生成して、その HTML に埋め込みます。ブラウザーが別のスタイルシートや JavaScript バンドルを読み込む必要はありません。

画像処理も同じビルドグラフに含まれています。Markdown からローカル画像を参照すると、JPEG XL、WebP、PNG の各形式で複数のサイズが生成されます。ブラウザーは、対応している形式と表示に合ったサイズを選びます。

## ローカルでプレビューする

```sh
nix develop
./build.sh
python3 -m http.server --directory dist
```

GitHub Pages でも、生成された `dist/` ディレクトリの内容を配信しています。
