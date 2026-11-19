#!/bin/bash
# figs/*.tex (tikzpicture) -> figs/*.svg
cd "$(dirname "$0")/figs"
for f in *.tex; do
  b=${f%.tex}
  [ -f "$b.svg" ] && [ "$b.svg" -nt "$f" ] && continue
  cat > "_$b.tex" <<TEX
\documentclass[border=2pt]{standalone}
\usepackage{luatexja}
\usepackage{amsmath,amssymb}
\usepackage{tikz}
\usetikzlibrary{calc,intersections}
\newcommand{\ax}[4]{\draw[->] (#1,0)--(#2,0) node[right]{\scriptsize \$x\$};
  \draw[->] (0,#3)--(0,#4) node[above]{\scriptsize \$y\$};
  \node[below left] at (0,0){\scriptsize O};}
\begin{document}
$(cat "$f")
\end{document}
TEX
  lualatex -interaction=nonstopmode -halt-on-error "_$b.tex" >/dev/null 2>&1 || { echo "FAIL $b"; continue; }
  pdftocairo -svg "_$b.pdf" "$b.svg"
  rm -f "_$b".*
done
