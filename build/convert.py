#!/usr/bin/env python3
"""類題集 tex -> JSON 変換。
問題・解答を番号で対応づけ、本文を HTML(数式は KaTeX 用に生 TeX のまま)に変換する。
TikZ は figs/<id>.tex に書き出し、後段 (figs.sh) で SVG 化する。
"""
import html, json, re, sys
from pathlib import Path

BUILD = Path(__file__).parent
FIGDIR = BUILD / 'figs'
FIGDIR.mkdir(exist_ok=True)
unknown = {}


def read_group(s, i, o='{', c='}'):
    """s[i] == o を前提に、対応する閉じ括弧までの中身と終端位置を返す"""
    assert s[i] == o, (s[i:i + 30])
    depth, j = 0, i
    while j < len(s):
        ch = s[j]
        if ch == '\\':
            j += 2
            continue
        if ch == o:
            depth += 1
        elif ch == c:
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    raise ValueError('unbalanced: ' + s[i:i + 50])


def skip_ws(s, i):
    while i < len(s) and s[i] in ' \t':
        i += 1
    return i


def find_env_end(s, i, name):
    """s[i:] は \\begin{name} の直後。対応する \\end{name} の位置と終端を返す"""
    depth = 1
    pat = re.compile(r'\\(begin|end)\{' + re.escape(name) + r'\}')
    for m in pat.finditer(s, i):
        depth += 1 if m.group(1) == 'begin' else -1
        if depth == 0:
            return m.start(), m.end()
    raise ValueError('no end for ' + name)


def esc(t):
    return html.escape(t, quote=False)


class Conv:
    def __init__(self, fig_prefix):
        self.fig_prefix = fig_prefix
        self.nfig = 0
        self.figs = []

    def math(self, tex, display):
        tex = tex.strip()
        cls = 'dm' if display else 'm'
        tag = 'div' if display else 'span'
        return f'<{tag} class="{cls}">{esc(tex)}</{tag}>'

    def fig(self, code):
        self.nfig += 1
        fid = f'{self.fig_prefix}-{self.nfig}'
        (FIGDIR / f'{fid}.tex').write_text(code)
        self.figs.append(fid)
        return f'<span class="fig" data-fig="{fid}"></span>'

    def conv(self, s):
        out = []
        i = 0
        n = len(s)
        while i < n:
            ch = s[i]
            if ch == '%':
                j = s.find('\n', i)
                i = n if j < 0 else j + 1
                continue
            if ch == '$':
                if s.startswith('$$', i):
                    j = s.find('$$', i + 2)
                    out.append(self.math(s[i + 2:j], True))
                    i = j + 2
                else:
                    j = i + 1
                    while s[j] != '$' or s[j - 1] == '\\':
                        j += 1
                    out.append(self.math(s[i + 1:j], False))
                    i = j + 1
                continue
            if ch == '~':
                out.append('&nbsp;')
                i += 1
                continue
            if ch in '{}':
                if ch == '{':
                    inner, i = read_group(s, i)
                    out.append(self.conv(inner))
                else:
                    i += 1
                continue
            if ch == '\n':
                # 空行 = 段落
                j = i + 1
                while j < n and s[j] in ' \t':
                    j += 1
                if j < n and s[j] == '\n':
                    out.append('<br class="par">')
                    while j < n and s[j] in ' \t\n':
                        j += 1
                    i = j
                else:
                    out.append('\n')
                    i += 1
                continue
            if ch != '\\':
                out.append(esc(ch))
                i += 1
                continue
            # --- コマンド ---
            if s.startswith('\\[', i):
                j = s.find('\\]', i)
                out.append(self.math(s[i + 2:j], True))
                i = j + 2
                continue
            if s.startswith('\\(', i):
                j = s.find('\\)', i)
                out.append(self.math(s[i + 2:j], False))
                i = j + 2
                continue
            if s.startswith('\\\\', i):
                i += 2
                if i < n and s[i] == '*':
                    i += 1
                i2 = skip_ws(s, i)
                if i2 < n and s[i2] == '[':
                    _, i = read_group(s, i2, '[', ']')
                out.append('<br>')
                continue
            m = re.match(r'\\([a-zA-Z]+)\*?|\\(.)', s[i:])
            name = m.group(1) or m.group(2)
            i += m.end()
            if m.group(2):
                sym = {' ': ' ', ',': '&thinsp;', '%': '%', '&': '&amp;', '#': '#', '_': '_',
                       '$': '$', '{': '{', '}': '}', ';': ' ', '!': ''}
                if name in sym:
                    out.append(sym[name])
                else:
                    unknown[name] = unknown.get(name, 0) + 1
                continue
            if m.group(1):
                # 制御綴の後の空白は無視
                while i < n and s[i] in ' \t':
                    i += 1

            def arg():
                nonlocal i
                i = skip_ws(s, i)
                if i < n and s[i] == '{':
                    a, i = read_group(s, i)
                    return a
                a = s[i]
                i += 1
                return a

            def opt():
                nonlocal i
                j = skip_ws(s, i)
                if j < n and s[j] == '[':
                    a, i = read_group(s, j, '[', ']')
                    return a
                return None

            if name == 'begin':
                env = arg()
                start = i
                end_s, end_e = find_env_end(s, i, env)
                body = s[start:end_s]
                i = end_e
                out.append(self.env(env, body, s[s.rfind('\\begin', 0, start):end_e]))
            elif name == 'point':
                out.append(f'<span class="pt">▶ {self.conv(arg())}</span>')
            elif name in ('textbf',):
                out.append(f'<b>{self.conv(arg())}</b>')
            elif name == 'underline':
                out.append(f'<u>{self.conv(arg())}</u>')
            elif name == 'textsf':
                out.append(self.conv(arg()))
            elif name == 'fbox':
                a = arg()
                if a.startswith('\\phantom'):
                    out.append('<span class="blank"></span>')
                else:
                    out.append(f'<span class="box">{self.conv(a)}</span>')
            elif name == 'hspace':
                w = arg()
                if w.startswith('-'):
                    pass
                elif m.group(0).endswith('*'):
                    out.append(f'<span class="hsi" style="width:{w}"></span>')
                else:
                    out.append(f'<span class="hs" style="width:{w}"></span>')
            elif name == 'quad':
                out.append('<span class="hs" style="width:1em"></span>')
            elif name == 'qquad':
                out.append('<span class="hs" style="width:2em"></span>')
            elif name in ('vspace',):
                arg()
            elif name == 'renewcommand':
                arg(); arg()
            elif name in ('hfill', 'small', 'tiny', 'scriptsize', 'par', 'noindent', 'centering',
                          'sffamily', 'bfseries', 'clearpage', 'newpage', 'medskip', 'smallskip',
                          'bigskip', 'displaystyle'):
                if name == 'par':
                    out.append('<br class="par">')
            elif name == 'rpt':
                out.append(self.math('\\rpt{%s}' % arg(), False))
            elif name == 'text':
                out.append(self.conv(arg()))
            else:
                unknown[name] = unknown.get(name, 0) + 1
                out.append(esc('\\' + name))
        return ''.join(out)

    def env(self, env, body, full):
        if env == 'tikzpicture':
            return self.fig(full)
        if env in ('equation*', 'align*', 'gather*', 'equation', 'align', 'gather'):
            e = env.rstrip('*')
            inner = {'equation': body}.get(e, '\\begin{%sed}%s\\end{%sed}' % (e, body, e)) if e != 'gather' else '\\begin{gathered}%s\\end{gathered}' % body
            return self.math(inner, True)
        if env in ('cases', 'array'):
            return self.math(full, False)
        if env == 'enumerate':
            return self.enum(body)
        if env == 'multicols':
            body = re.sub(r'^\s*\{\d+\}', '', body)
            return f'<div class="mc2">{self.conv(body)}</div>'
        if env == 'center':
            return f'<div class="center">{self.conv(body)}</div>'
        if env == 'minipage':
            b = body.lstrip()
            if b.startswith('['):
                _, k = read_group(b, 0, '[', ']')
                b = b[k:].lstrip()
            w, k = read_group(b, 0)
            b = b[k:]
            mm = re.match(r'([\d.]+)\\linewidth', w)
            pct = float(mm.group(1)) * 100 if mm else 100
            hasfig = '\\begin{tikzpicture}' in b
            cls = 'mp mpfig' if hasfig else 'mp'
            return f'<div class="{cls}" style="--w:{pct:.0f}%">{self.conv(b)}</div>'
        if env == 'tabular':
            return self.tabular(body)
        if env == 'kai':
            return self.conv(body)
        unknown['env:' + env] = unknown.get('env:' + env, 0) + 1
        return esc(full)

    def enum(self, body):
        # \item を分割(ネストした enumerate は考慮)
        items = []
        depth = 0
        cur = None
        for tok in re.split(r'(\\item\b(?:\s*\[[^\]]*\])?|\\begin\{enumerate\}|\\end\{enumerate\})', body):
            if tok is None:
                continue
            if tok.startswith('\\item') and depth == 0:
                lab = re.search(r'\[([^\]]*)\]', tok)
                cur = [lab.group(1) if lab else None, '']
                items.append(cur)
                continue
            if tok == '\\begin{enumerate}':
                depth += 1
            elif tok == '\\end{enumerate}':
                depth -= 1
            if cur is not None:
                cur[1] += tok
        k = 0
        lis = []
        for lab, txt in items:
            if lab is None:
                k += 1
                lab = f'({k})'
            lis.append(f'<div class="it"><span class="lab">{esc(lab)}</span><div class="itb">{self.conv(txt.strip())}</div></div>')
        return '<div class="enum">' + ''.join(lis) + '</div>'

    def tabular(self, body):
        spec, k = read_group(body, 0)
        body = body[k:]
        # 縦線の位置: 各列の右側に | があるか
        cols = []
        for c in spec:
            if c in 'lcr':
                cols.append({'a': c, 'r': False})
            elif c == '|' and cols:
                cols[-1]['r'] = True
        rows = re.split(r'\\\\', body)
        trs = []
        for r in rows:
            hl_before = False
            r = r.strip()
            line_after = False
            if r.startswith('\\hline'):
                r = r[6:].strip()
                if trs:
                    trs[-1][1] = True
                else:
                    hl_before = True
            if not r:
                continue
            cells = r.split('&')
            tds = []
            for ci, cell in enumerate(cells):
                col = cols[ci] if ci < len(cols) else {'a': 'c', 'r': False}
                cl = 'br' if col['r'] else ''
                tds.append(f'<td class="{cl} a{col["a"]}">{self.conv(cell.strip())}</td>')
            trs.append([''.join(tds), False])
        h = ''.join(f'<tr class="{"bb" if b else ""}">{t}</tr>' for t, b in trs)
        return f'<div class="tblwrap"><table class="tb">{h}</table></div>'


def parse(path, book, label):
    src = Path(path).read_text()
    body = src[src.index('\\begin{document}') + 16:src.index('\\end{document}')]
    ai = body.index('\\shouans')
    # 解答見出し(\Huge 解答)の前で問題パートを切る
    hz = body.rfind('{\\sffamily\\bfseries\\Huge 解答', 0, ai)
    qpart = body[:hz if hz >= 0 else ai]
    apart = body[ai:]
    chapters = []
    probs = {}
    def cmds(text, names):
        """\\name{a}{b} を括弧対応で見つけ (name, a, b, start, end) を列挙"""
        res = []
        for m in re.finditer(r'\\(' + '|'.join(names) + r')\{', text):
            a, k = read_group(text, m.end() - 1)
            b, k = read_group(text, k)
            res.append((m.group(1), a, b, m.start(), k))
        return res
    chapters = []
    probs = {}
    ch = None
    cur = None
    marks = cmds(qpart, ['shou', 'mon'])
    for idx, (nm, a, b, st, en) in enumerate(marks):
        nxt = marks[idx + 1][3] if idx + 1 < len(marks) else len(qpart)
        if nm == 'shou':
            ch = {'no': len(chapters) + 1, 'name': a, 'title': b}
            chapters.append(ch)
        else:
            num = int(a)
            probs[num] = {'id': f'{book}-{num}', 'book': book, 'no': num, 'title': b,
                          'ch': ch['no'], 'q': qpart[en:nxt]}
    for nm, a, b, st, en in cmds(apart, ['ans']):
        num = int(a)
        k = apart.index('\\begin{kai}', en)
        e, _ = find_env_end(apart, k + len('\\begin{kai}'), 'kai')
        probs[num]['a'] = apart[k + len('\\begin{kai}'):e]
    conv = Conv(book)
    out = []
    for num in sorted(probs):
        p = probs[num]
        q = re.sub(r'\\clearpage\s*$', '', p['q'].strip())
        conv.fig_prefix = f'{book}-{num}-q'; conv.nfig = 0
        p['q'] = conv.conv(q).strip()
        conv.fig_prefix = f'{book}-{num}-a'; conv.nfig = 0
        p['a'] = conv.conv(p['a'].strip()).strip()
        p['title'] = conv.conv(p['title'])
        out.append(p)
    return {'id': book, 'label': label, 'chapters': chapters, 'problems': out}


if __name__ == '__main__':
    up = Path(sys.argv[1]) if len(sys.argv) > 1 else BUILD.parent / 'src'
    books = [
        parse(next(up.glob('*IA*.tex')), 'IA', '数学Ⅰ・A'),
        parse(next(up.glob('*IIBC*.tex')), 'IIBC', '数学Ⅱ・B・C'),
    ]
    (BUILD / 'data.json').write_text(json.dumps(books, ensure_ascii=False))
    for b in books:
        print(b['id'], len(b['problems']), 'problems,', len(b['chapters']), 'chapters')
    print('unknown:', unknown)
