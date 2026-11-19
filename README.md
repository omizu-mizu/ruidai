# 基礎問題演習 Ⅰ・A／Ⅱ・B・C（類題カード）

数学Ⅰ・A／Ⅱ・B・C 類題集の単語帳形式アプリ。問題をタップすると解答が出て、理解度を4段階で記録できる（記録は各端末のブラウザに保存）。

公開ページ: https://omizu-mizu.github.io/ruidai/

## 作り直し方

`src/*.tex` を修正したら:

```bash
cd build
npm install          # 初回のみ (KaTeX)
python3 convert.py   # tex -> data.json, 図を figs/*.tex に書き出し
./figs.sh            # TikZ -> SVG（lualatex と pdftocairo が必要。変更のあった図だけ再生成）
python3 build.py     # -> ../index.html
node test.js         # 全問の表示チェック（Playwright）
```
