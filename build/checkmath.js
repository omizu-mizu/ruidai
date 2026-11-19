const katex=require('katex');const d=require('./data.json');
const macros={'\\rpt':'0.\\dot{#1}'};
let n=0,bad=0;
const re=/<(span|div) class="(m|dm)">([\s\S]*?)<\/\1>/g;
const un=s=>s.replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');
for(const b of d)for(const p of b.problems)for(const k of ['title','q','a']){
  for(const m of p[k].matchAll(re)){n++;
    try{katex.renderToString(un(m[3]),{displayMode:m[2]=='dm',macros:{...macros},strict:'error',throwOnError:true})}
    catch(e){bad++;console.log(p.id,k,e.message.slice(0,140))}}}
console.log(n,'math',bad,'errors');
