#!/usr/bin/env python3
"""data.json + figs/*.svg + KaTeX -> ../類題カード.html (1ファイル完結)"""
import base64, json, re
from pathlib import Path

B = Path(__file__).parent
K = B / 'node_modules/katex/dist'

css = (K / 'katex.min.css').read_text()
# フォントは woff2 のみ base64 で埋め込む
def font(m):
    name = m.group(1)
    data = base64.b64encode((K / 'fonts' / f'{name}.woff2').read_bytes()).decode()
    return f'src:url(data:font/woff2;base64,{data}) format("woff2")'
css = re.sub(r'src:url\(fonts/([\w-]+)\.woff2\) format\("woff2"\)(?:,url\([^)]*\) format\("[^"]*"\))*', font, css)
assert 'fonts/' not in css
js = (K / 'katex.min.js').read_text()

books = json.loads((B / 'data.json').read_text())
# 和文の行内改行(LaTeX では空白にならない)を除く
cjk = r'[　-ヿ一-鿿＀-￯]'
for b in books:
    for p in b['problems']:
        for k in ('q', 'a', 'title'):
            s = p[k]
            s = re.sub(rf'(?<={cjk})\n(?={cjk})', '', s)
            s = re.sub(r'^(\s|<br class="par">)+|(\s|<br class="par">|<br>)+$', '', s)
            # 行頭の \hspace* は、その行全体のぶら下げ字下げにする
            seg = r'(?:[^<]|<(?!/?div|br\b))*?'
            prev = None
            while prev != s:
                prev = s
                s = re.sub(r'(^|<br>|<br class="par">|<div[^>]*>|</div>)(\s*)<span class="hsi" style="width:([^"]+)"></span>(' + seg + r')(<br>|(?=<br class="par">)|(?=</div>)|$)',
                           lambda m: f'{m.group(1)}{m.group(2)}<div class="ind" style="padding-left:{m.group(3)}">{m.group(4)}</div>', s)
            s = s.replace('<span class="hsi"', '<span class="hs"')
            p[k] = s

figs = {}
for f in sorted((B / 'figs').glob('*.svg')):
    svg = f.read_text()
    w = float(re.search(r'width="([\d.]+)', svg).group(1))
    figs[f.stem] = {'w': w, 'src': 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode()}

html = (B / 'app.html').read_text()
for key, val in [('/*KATEX_CSS*/', css), ('/*KATEX_JS*/', js),
                 ('/*DATA*/', json.dumps(books, ensure_ascii=False).replace('</', '<\\/')),
                 ('/*FIGS*/', json.dumps(figs))]:
    html = html.replace(key, val, 1)
out = B.parent / 'index.html'
out.write_text(html)
print(out, f'{len(html.encode())/1e6:.2f} MB')
