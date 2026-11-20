---
title: このサイトを軽量にするためにしたこと
date: 2026-11-20
summary: 独自のビルド手順を使ってMarkdownから静的ページを生成する流れ
---

## はじめに
このページはこのサイトをどのように設計したのかについて、私なりに工夫した点についてまとめている。
このページは**markdownで記述**され、主にCに使われるビルドツール**ninjaも用いて静的サイトを生成**されている。
なぜそのような設計にしたかも含めて書いていこうかと思う。

この記事は、画像やCSSを含めても、gzip圧縮後で約 **@@PAGE-TOTAL-GZIP@@** になった。内訳と測り方は「実際のページサイズ」で紹介する。

## ウェブサイト設計の方針
最近は様々な方法でウェブサイトが作られているが、そのサイズが年々増加傾向にある。
HTTP Archive[^archive]によると、2026年11月時点でのデスクトップ向けページのサイズの中央値は**約3MB**である。つまり、一部の特に重いページが平均を押し上げているという話ではなく、調査対象の約半数がこのサイズ以上ということだ。

インターネットが高速になったおかげで気がつくことは少ないが、3MBはかなり大きな数字である。
3MBこのような内容である

- 印刷用紙が1500枚分(1枚あたり約2KB程度の文字数印刷できるとする[^paper])
- ビル・ゲイツが過去にこれ以上に必要ないといったHDDサイズの約4.6倍[^bill]
- MP3の楽曲1つ程度[^mp3]


他にもいくつか例は挙げられるが[^howbig][^filesize]、このようなテキストが基本のページで3MB使うのは非常にもったいない。

この記事の元のMarkdownファイルは **@@PAGE-MARKDOWN@@** しかない。
それをレンダリングするために、数百KBのJavascriptライブラリを読み込んで数百KBのスタイルシートを読み込んで、さらに広告までつけてしまうのは非常にもったいなく感じられる。

このサイトの内容は基本的にテキストベースでたまに図が出てくる程度なので、一つ一つのページをできるだけ軽量にしたい。

[^archive]: <https://httparchive.org/reports/page-weight>
[^paper]: <https://www.techwalla.com/articles/how-many-printed-pages-is-one-megabyte>
[^mp3]: <https://filesize.org/calculators/audio-file-size/>
[^bill]: <https://www.computerworld.com/article/1563853/the-640k-quote-won-t-go-away-but-did-gates-really-say-it.html>
[^howbig]: <https://usefoyer.com/how-big-is/1-megabyte>
[^filesize]: <https://kordu.tools/blog/file-size-reference-how-big-is-a-megabyte/>

## どうすればページは軽量になるのか。
**ページをHTMLだけで記述すれば良い。**
以上

## (再)どうすればページは軽量になるのか。
もちろんモダンな見た目のページを作るためにはHTMLだけでは足りなくなってきている。
HTMLだけを利用する利点も多くあるが[^vanilla][^14k]、軽くデザインを調整したい、少し動的なコンテンツを設定したいなどの要望はやりある。(このページの場合テーマ選択にJSが使われている。)

そこで必要最低限だけのCSSとJSが含まれるようにする。
例えばCSSのライブラリであるTailwindはソースをすべて読み込み必要なCSSだけを出力することができる。
また、テーマ選択程度であればライブラリは必要ないので直接書き込めば良い。

[^vanilla]: <https://www.vanillahtml.com/blog/html-is-enough>
[^14k]: <https://jaimebuilds.com/lab/the-14kb-rule/>

## Markdownのレンダリング
では書かれたMarkdownをどのようにHTMLに変換するのか。
一般的にはHugo[^hugo]やVuepress[^vuepress]等の静的サイトジェネレータを活用することが多い。しかし、独自のビルドパイプラインが必要な際には汎用のビルドツールを使うてもある。
特にAIが使える現在、MarkdownからHTMLを適当なテンプレートを使ったレンダリングをするというスクリプトを書くのは非常に簡単である。
何なら自分で書くとしてもMarkdownの読み込みはそこまで難しくないため、独自のレンダリングエンジンを作るのはそこそこ容易である。
本サイトはAIに作らせたPythonのスクリプトでhtmlを生成し、画像の返還等の処理を含めてninja[^ninja]と呼ばれるビルドツールでビルドしている。

ninjaは主にcmakeやmesonなどのC,C++のビルドツールとして使われがちだが、任意のビルドグラフを実行するプログラムなので例えば次のような処理：

- MarkdownをHTMLにレンダリングする
- 複数のMarkdownファイルをパースしてインデクスを作成する
- 資料として使いたい写真を複数のフォーマット(jxl,webp,png)に変換する

などの処理をまとめたビルドグラフを高速に処理してくれる。

![build.shがconfigure.pyを呼び出してbuild.ninjaを生成する。Ninjaはその定義に従い、Markdown・Jinja・YAMLからHTMLを、site.cssとJinjaテンプレートから共通CSSを、元画像からJPEG XL・WebP・PNGを生成し、すべてdist/に出力する。](media/build-pipeline.svg "静的サイトのビルドグラフ")

`configure.py`はファイルの依存関係を`build.ninja`に書き出す。変換を実行するのはNinjaで、入力に変更があれば、それに依存する出力だけを作り直す。HTMLと共通CSSは別々に生成するので、完成したHTMLをTailwindに渡す必要はない。

たとえば`styles/site.css`だけを編集すると、NinjaはCSSを再生成するが、MarkdownからHTMLへの変換はやり直さない。生成されたCSSが変われば、この記事のサイズを再計測して数値だけを埋め直す。

単純にHTMLのレンダリングをするだけであれば既存の仕組みを使うほうが良いのではないかと思う方もいると思うが、この仕組みを使った面白いことがこのページサイズの計測のために使われているのでもう少し読んでもらいたい。
また、この仕組みを応用して、watchexec[^watchexec]と組み合わせたLive Reloadも簡単に実現できている。

[^hugo]: <https://gohugo.io/>
[^vuepress]: <https://vuepress.vuejs.org/>
[^ninja]: <https://ninja-build.org/>
[^watchexec]: <https://watchexec.github.io/>

## 表示するためにはHTMLしかいらない
このページはHTMLのみで表示できる。
先程の節でCSSとJSを以下に導入するかと言う話をしたあとで混乱するかもしれないが、重要なのはHTMLに本文が含まれているので、HTMLのみでも情報が完結しているということである。
JavaScriptやCSSはあくまで補助的な役割でしかないため、このページではこれら無しでHTMLだけでレンダリングも可能である。

ブラウザで読み込む場合にはCSSがロードされてからレンダリングが開始されるため、HTMLだけでレンダリングはされない。
しかし、別のページに遷移した際に使用されるCSSは同一のもののためキャッシュされたCSSが使用され実質的にHTMLのダウンロードのみでレンダリングは完結する。

## 実際のページサイズ

- **元のMarkdown**：@@PAGE-MARKDOWN@@
- **HTMLだけ**：@@PAGE-HTML@@（gzip圧縮後：@@PAGE-HTML-GZIP@@）
- **HTMLとすべてのアセット**：@@PAGE-TOTAL@@（gzip圧縮後：@@PAGE-TOTAL-GZIP@@）

![page_size.pyは元のMarkdown、レンダリング済みのHTML、配信用アセットからそれぞれのサイズを求める。計測値と元のHTMLを合わせ、プレースホルダーを置き換えた公開用HTMLをdist/に書き出す。](media/page-size-build.svg "ページサイズをHTMLに埋め込む手順")

2節前にどうしてninjaを用いてわざわざ複雑なビルドを行うのか不思議に感じらてた方もいるかもしれないが、このようなレンダリング結果のサイズを埋め込むような面白い実装も静的に記述できるからである。
もちろんこれはJavascriptを用いていない。

Ninjaでは、元のMarkdown、計測前のHTML、配信用アセットを計測ステップの入力にしている。Markdownは元ファイルのバイト数をそのまま示す。配信時に送られないので、ページ全体のサイズには含めない。ページ全体の計測では、HTML本体と、そこから直接参照するローカルのファイル（共通CSS、図、ファビコン）を重複なく数える。非圧縮の値はそれぞれのファイルのバイト数の合計で、gzipの値は各ファイルを別々にレベル9で圧縮したときの合計だ。

計測が終わったら、Markdownに書いたプレースホルダーを生成済みのHTML内で数値に置き換える。この置き換えでHTMLのサイズがわずかに変わるため、表示している値は概算になる。また、HTTPヘッダーやキャッシュは考慮していないので、ブラウザーでの実際の転送量とは異なる。

## デプロイ
Github Pagesのようなプラットフォームは静的なHTMLファイルを投稿するのに最適なので今回はそれを活用している。
Github Actionsでビルドを行い、成果物がここに表示されている。

Github Actionsの実行履歴を見てもらえばわかることだが、デプロイには40s程度、レンダリングだけで見ると2数秒程度しかかかっていない。

![GitHub Actionsがサイトをビルドし、生成されたdist/だけをGitHub Pagesに公開する。](media/pages-deploy.svg "GitHub Pagesに公開するまでの流れ")

## まとめ
現在主流のウェブサイトの作成方法では非常に単純なページでも簡単に数MBに達してしまうが、本ページはそうならないように設計をした。
そのためにPythonを使ったMarkdownのレンダリングと素材の前処理を一括で処理するためのビルドグラフを作成し、ninjaを使ってビルドしている。

制定機サイトを今後作ろうと考えている方がいれば、このサイトのようにフレームワークを用いずに実装することは可能なので、このように軽量なサイトにしてみてはいかがだろうか。