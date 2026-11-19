const {chromium}=require('playwright');
(async()=>{
 const b=await chromium.launch();const pg=await b.newPage({viewport:{width:390,height:844}});
 const errs=[];pg.on('pageerror',e=>errs.push(e.message));
 await pg.goto('file://'+require('path').resolve(__dirname,'../index.html'));
 const r=await pg.evaluate(()=>{
   const out=[];
   for(const p of ALL){
     startSession([p.id]); reveal();
     const card=document.querySelector('#card');
     const ke=[...card.querySelectorAll('.katex-error')].map(e=>e.title||e.textContent);
     const txt=card.innerText;
     const bs=(txt.match(/\\[a-zA-Z]+/g)||[]);
     const wide=card.scrollWidth>card.clientWidth+2;
     if(ke.length||bs.length||wide) out.push([p.id,ke.slice(0,2),bs.slice(0,5),wide?'WIDE '+card.scrollWidth:'']);
   }
   return out;});
 console.log(JSON.stringify(r,null,0).replace(/\],\[/g,'],\n['));console.log('pageerrors',errs);
 await b.close();})();
