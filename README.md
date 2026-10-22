# Quarto HTML slides

QuartoのQMDから、アニメーションを内包する**単一HTML**と、各ページの**最終stepを収めたPDF**を生成します。HTMLは単体でオフライン閲覧できます。npmは使いません。

## まず見る

[例のHTML](output/nco-intro.html) · [例のPDF](output/nco-intro.pdf) · [QMD](decks/nco-intro/slides.qmd) · [スライド案](decks/nco-intro/memo.md)

GitHub上ではHTMLのソースが表示されます。Rawからダウンロードし、ブラウザで開いてください。スマホもHTMLをブラウザで開きます（ファイル管理アプリ内の簡易プレビューはJavaScriptが動かない場合があります）。

## 準備

[Quarto CLI](https://quarto.org/docs/get-started/) と [uv](https://docs.astral.sh/uv/getting-started/installation/) をインストールして、このフォルダで実行します。

```sh
uv sync
uv run playwright install chromium
uv run scripts/slides.py build nco-intro
```

PDFはPlaywright同梱のChromiumで生成します。Linuxでは必要に応じて `uv run playwright install --with-deps chromium` でOS依存も用意します。

## 新しいスライド

```sh
uv run scripts/slides.py new my-talk
# または既存の発表をコピー
uv run scripts/slides.py new my-talk --from nco-intro
```

`decks/my-talk/slides.qmd`を編集し、以下を実行します。

```sh
uv run scripts/slides.py build my-talk
```

出力は `output/my-talk.html` と `output/my-talk.pdf`。このコマンドはブラウザ検査まで行い、エラー・外部通信・検出可能な重なりがあると失敗します。

AIへの依頼例：

> このスライド案で、新しいスライド「my-talk」を作って。対象読者は学部生、結論は……。図は最初に……を表示し、次のstepで……に変える。

情報不足や説明の流れに問題がある場合、AIは作成前に質問します。編集後はHTML/PDFを生成して閲覧リンクを返します。

## 構成

```text
decks/<名前>/
  slides.qmd       # # は章、## は1枚
  images/          # この発表の画像
  styles/slides.css
  memo.md          # スライド案
  reference.bib
html/<図名>/index.html  # 発表をまたいで共有するHTML図
shared/                # 表示・キー操作・引用スタイル
scripts/slides.py       # uvで動く唯一のコマンド入口
templates/deck/         # 新規作成の雛形
output/                # 配布するHTMLとPDF
```

QuartoでMarkdownと文献をHTMLへ変換し、小さな専用プレイヤーへ組み込みます。Reveal.jsの標準キー操作に依存しないため、上下と左右を別の役割にできます。Quartoの生成中間ファイルと検査画像は `.build/` に置き、Gitには含めません。

## アニメーション

```sh
uv run scripts/slides.py animation route-example
```

表示されたiframe行をQMDへ追加し、`html/route-example/index.html`を編集します。

```html
<iframe src="../../html/route-example/index.html" title="経路の構成"></iframe>
```

図のAPIは1つです。stepは0からstepsまで（以下は計3状態）。

```js
registerAnimation({
  steps: 2,
  render(step) {
    // stepだけから描画を決める。0→2や2→0にも対応する。
  }
});
```

共有 `frame.js` を読み込む雛形が自動生成されます。親プレイヤーがstepを管理し、複数iframeは同時進行、短い図は最終stepで止まります。自動再生タイマーは使わず、最終状態を確定させてください。本文も `<div data-step="1">…</div>` で段階表示できます。

表の数値などを順に強調するときは `[0.04%]{.highlight data-highlight-step="1"}` と書きます。指定stepで背景がハイライトされ、戻すと解除されます。PDFでは最後の強調状態を出力します。

画像・CSS・通常のJS・iframeはビルド時に内包します。外部CDN・CSSの `@import`・`srcset` は使いません。静的なローカルES moduleのimportはPythonで内包します。動的fetchや外部importは避け、必要なデータをローカルへ用意します。コードセルを実行する構成は雛形に含みません。

## 引用

`reference.bib`に文献を登録し、QMDで `[@key]` と書くと本文は `[1]`、同じページの下端には小さな書誌情報が入ります。引用が多すぎるページは分割してください。引用が1件でもある場合、末尾に参考文献ページを自動生成します。QMDでは `## 参考文献 {#references}` と書くとその見出しを展開し、省略しても自動で補完します。引用済み文献を5件ずつ掲載し、ページ内フッターも残します。

## 操作

| 操作 | 動作 |
|---|---|
| ↑ / ↓ | 前 / 次のページ |
| ← / → の短押し | 前 / 次のstep。端では前 / 次のページ |
| ← / → の長押し（450ms） | 現在のページの最初 / 最後のstep |
| 画面の左30%をタップ | 戻る |
| 残り70%をタップ | 進む |
| ☰ / O / Escape | 一覧 |
| ⛶ / F | 全画面（対応ブラウザ） |

`#`の章ごとに一覧を横並びにします。章がない発表は4列です。全画面APIに非対応のブラウザでは、その旨をボタンに表示します。スマホは横向きにすると図や本文を大きく見られます。

## 検査

```sh
uv run scripts/slides.py check nco-intro
uv run playwright install webkit  # Safari系の追加テスト用（任意）
uv run python -m unittest discover -s tests
```

ビルド時は全stepのはみ出し・本文同士や引用フッターとの重なり、外部通信、ブラウザエラーを確認します。PCのキー操作とスマホサイズのタップも検査します。`.build/<名前>/01.png`等が各ページの最終状態、`mobile.png`がスマホ表示、`checks.json`が検査結果です。

自動検査はSVG内の意図的な線・図形の重なりや、文章の意味までは判定しません。画像とPDFを目視確認してください。PDFは文字を保持し、アニメーションだけ最終状態で固定します。

制作ルールは [AGENTS.md](AGENTS.md)、最小限のAIスキルは [.agents/skills/quarto-slides/SKILL.md](.agents/skills/quarto-slides/SKILL.md) にあります。

検証環境：Quarto 1.8.26、Python 3.13、Playwright Chromium / WebKit。iPhone 13相当のエミュレーションでタップと一覧を確認済みです。実機での確認は別途必要です。


例の図・本文・青い見出し帯は20261014を基準にしています。`html/shared/motion.mjs`が元のSVG要素を保持して補間し、`runtime.mjs`のアダプターがプレイヤーへ接続します。図の停止点・中間の遷移・時間は元の定義を使用します。`shared/original-slides.css`が元の見た目、`player-layout.css`がプレイヤーとの接続部分です。
