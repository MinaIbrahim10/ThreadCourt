// DOM integration, not visual/browser QA. Requires jsdom and an installed package.
const {JSDOM,VirtualConsole}=require('jsdom');
const assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const net=require('node:net');
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function until(predicate,label){
  for(let i=0;i<300;i++){if(await predicate())return;await delay(20);}
  throw Error('Timed out: '+label);
}
(async()=>{
  const results=[];
  for(const scenario of ['lost-update','lock-inversion']){
    const socket=net.createServer();
    await new Promise(resolve=>socket.listen(0,'127.0.0.1',resolve));
    const port=socket.address().port;
    await new Promise(resolve=>socket.close(resolve));
    const server=spawn(process.env.PYTHON||'python',['-c',
      'import sys; from threadcourt.agents import investigate; from threadcourt.dashboard import serve; serve(investigate(sys.argv[1]),int(sys.argv[2]))',scenario,String(port)],{stdio:'ignore'});
    let dom;
    try{
      const base='http://127.0.0.1:'+port;
      await until(async()=>{try{return(await fetch(base)).ok;}catch{return false;}},'server');
      const errors=[],console=new VirtualConsole();console.on('jsdomError',e=>errors.push(e.message));
      dom=await JSDOM.fromURL(base,{resources:'usable',runScripts:'dangerously',virtualConsole:console,beforeParse(window){
        window.fetch=(url,options)=>fetch(new URL(url,base),options);
        const interval=window.setInterval.bind(window);
        window.setInterval=(fn,ms,...args)=>interval(fn,ms===650?5:ms,...args);
      }});
      const document=dom.window.document,$=id=>document.getElementById(id);
      await until(()=>$('traceStatus').textContent.includes('verified'),'trace report');
      assert.equal($('before').textContent,'violation-found');
      assert.equal($('after').textContent,'no-violation-in-model');
      const count=document.querySelectorAll('#trace tr').length;
      assert.ok(count>0);
      $('step').value=1;$('step').dispatchEvent(new dom.window.Event('input'));
      assert.equal(document.querySelectorAll('#trace tr.active').length,1);
      $('play').click();
      await until(()=>document.querySelectorAll('#trace tr.active').length===count,'play trace');
      assert.equal(document.querySelectorAll('#agents .agent').length,5);
      assert.ok(document.querySelectorAll('#agents .pill').length===5);
      const download=document.querySelector('a[download]');
      const report=await(await fetch(new URL(download.getAttribute('href'),base))).json();
      assert.equal(report.replayed,true);
      assert.equal(report.before.violation.trace.length,count);
      if(scenario==='lost-update')assert.ok(document.body.textContent.includes('counter 1 / expected 2 → repaired 2 / expected 2'));
      assert.deepEqual(errors,[]);
      results.push({scenario,traceTransitions:count,replay:true,download:true,javascriptErrors:errors});
    }finally{
      dom?.window.close();server.kill();
      await new Promise(resolve=>server.exitCode!==null?resolve():server.once('exit',resolve));
    }
  }
  process.stdout.write(JSON.stringify({kind:'DOM integration; no visual QA',results},null,2)+'\n');
})().catch(error=>{console.error(error);process.exitCode=1;});
