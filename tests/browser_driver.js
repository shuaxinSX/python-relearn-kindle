/* Real Chromium regression against generated HTML served over HTTP. Dev only. */
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const acorn = require('acorn');
const url = process.argv[2];
const KEY = 'python-relearn:python-relearn-v1:state';
const fresh = () => ({schemaVersion:1, courseId:'python-relearn', settings:{fontSize:26}, lastLocation:null, lessons:{}, questions:{}});
const results = [];
let browser;
async function check(name, fn, opts={}) {
 if(process.env.PRL_BROWSER_FILTER && !name.includes(process.env.PRL_BROWSER_FILTER)) return;
 const context = await browser.newContext(opts);
 const page = await context.newPage();
 page.setDefaultTimeout(5000);
 const errors = [];
 page.on('pageerror', e=>errors.push(String(e)));
 page.on('dialog', d=>d.accept());
 try { await fn(page, context); assert.deepEqual(errors,[]); results.push({name,pass:true}); }
 catch(e) { results.push({name,pass:false,error:String(e.stack)}); console.error(name+': '+e.stack); }
 finally { await context.close(); }
}
async function seed(page, state) {
 await page.goto(url+'index.html');
 await page.evaluate(([key,state])=>localStorage.setItem(key,typeof state==='string'?state:JSON.stringify(state)),[KEY,state]);
}
async function state(page) {return page.evaluate(key=>JSON.parse(localStorage.getItem(key)),KEY);}
async function active(page, id) {await page.waitForFunction(id=>document.querySelector('.step.active')?.id===id,id);}
async function qrev(page, qid) {return Number(await page.locator(`[data-question-id="${qid}"]`).getAttribute('data-question-revision'));}
async function answer(page, value) {
 await page.locator('.step.active input[value="'+value+'"]').check();
 await page.locator('.step.active .quiz-submit').click();
}
(async()=>{
 browser=await chromium.launch();
 await check('A1 fresh home and lesson initialization',async p=>{
  await p.goto(url+'index.html');
  assert.equal(await p.locator('#home-primary').innerText(),'开始学习');
  await p.locator('#home-primary').click();
  await active(p,'s-goal');
  assert.equal(await p.locator('.step:visible').count(),1);
  assert.equal(await p.locator('.quiz input:checked').count(),0);
  await p.getByRole('button',{name:'下一部分',exact:true}).click(); await active(p,'s-what-is-python');
  assert.equal((await state(p)).lastLocation.stepId,'s-what-is-python');
  await p.goto(url+'index.html'); assert.equal(await p.locator('#home-primary').innerText(),'继续学习');
  assert.match(await p.locator('#home-primary').getAttribute('href'),/#s-what-is-python$/);
 });
 await check('A2 anchors, reload, history and deleted step fallback',async p=>{
  await p.goto(url+'lessons/run-and-bindings.html#s-predict'); await active(p,'s-predict');
  await p.getByRole('button',{name:'下一部分',exact:true}).click(); await active(p,'s-misconception');
  await p.goBack(); await active(p,'s-predict'); await p.goForward(); await active(p,'s-misconception');
  await p.reload(); await active(p,'s-misconception');
  await p.goto(url+'lessons/run-and-bindings.html'); await active(p,'s-misconception');
  await p.goto(url+'lessons/run-and-bindings.html#deleted'); await active(p,'s-goal');
  assert.equal(await p.evaluate(()=>document.activeElement.tagName),'H2');
 });
 await check('A2 saved location survives a real browser restart',async()=>{
  const profile=fs.mkdtempSync(path.join(os.tmpdir(),'prl-browser-'));
  let persistent;
  try {
   persistent=await chromium.launchPersistentContext(profile);
   let p=await persistent.newPage();
   await p.goto(url+'lessons/strings.html#s-predict');await active(p,'s-predict');
   await persistent.close();persistent=undefined;
   persistent=await chromium.launchPersistentContext(profile);
   p=await persistent.newPage();await p.goto(url+'index.html');
   assert.match(await p.locator('#home-primary').getAttribute('href'),/strings.html#s-predict$/);
   await p.locator('#home-primary').click();await active(p,'s-predict');
  } finally {if(persistent)await persistent.close();fs.rmSync(profile,{recursive:true,force:true});}
 });
 await check('A3 submit, repeat submit, refresh, retry and review isolation',async p=>{
  await p.goto(url+'lessons/run-and-bindings.html#s-quiz-1');
  await p.locator('.step.active .quiz-submit').click();
  assert.equal(Object.keys((await state(p)).questions).length,0);
  await answer(p,'a'); let s=await state(p); assert.equal(s.questions['run-and-bindings-q1'].attempts,1);
  await p.locator('.step.active .quiz-form').dispatchEvent('submit');
  assert.equal((await state(p)).questions['run-and-bindings-q1'].attempts,1);
  assert(!p.url().includes('q-run')); await p.reload();
  assert.equal(await p.locator('.step.active .quiz-submit').isDisabled(),true);
  assert.equal((await state(p)).questions['run-and-bindings-q1'].attempts,1);
  await p.goto(url+'lessons/strings.html#s-predict'); const normal=(await state(p));
  await p.goto(url+'review.html'); assert.equal(await p.locator('#review-list li').count(),1);
  await p.locator('#review-list a').click();
  await p.locator('.step.active .quiz-retry').click();
  assert.equal((await state(p)).questions['run-and-bindings-q1'].needsReview,true);
  await answer(p,'b'); s=await state(p);
  assert.equal(s.questions['run-and-bindings-q1'].attempts,2); assert.equal(s.questions['run-and-bindings-q1'].wrongAttempts,1);
  assert.equal(s.questions['run-and-bindings-q1'].needsReview,false);
  assert.deepEqual(s.lastLocation,normal.lastLocation); assert.deepEqual(s.lessons,normal.lessons);
  await p.reload();assert.equal(await p.locator('.step.active .quiz-back-review').isVisible(),true);
  await p.locator('.step.active .quiz-back-review').click(); assert.equal(await p.locator('#review-list li').count(),0);
  assert.equal(await p.locator('#review-empty').isVisible(),true);
 });
 await check('A3 maximum imported counters stay valid after retry',async p=>{
  await p.goto(url+'lessons/run-and-bindings.html');const revision=await qrev(p,'run-and-bindings-q1');
  const s=fresh();s.questions['run-and-bindings-q1']={revision,attempts:Number.MAX_SAFE_INTEGER,wrongAttempts:Number.MAX_SAFE_INTEGER,lastOptionId:'a',lastCorrect:false,needsReview:true};
  await seed(p,s);await p.goto(url+'lessons/run-and-bindings.html#s-quiz-1');
  await p.locator('.step.active .quiz-retry').click();await answer(p,'a');await p.reload();
  assert.equal(await p.locator('#save-banner').isVisible(),false);
  assert.equal((await state(p)).questions['run-and-bindings-q1'].attempts,Number.MAX_SAFE_INTEGER);
 });
 await check('A4 read and practice independent and reversible',async p=>{
  await p.goto(url+'lessons/conditions.html#s-practice');
  assert.equal(await p.locator('#mark-read').isVisible(),true);
  await p.locator('#mark-read').click();
  let s=await state(p); assert.equal(s.lessons.conditions.completed,true); assert.equal(s.lessons.conditions.practiceDone,false); assert.deepEqual(s.questions,{});
  await p.locator('.practice-done input').check(); await p.reload();
  assert.equal(await p.locator('.practice-done input').isChecked(),true);
  await p.goto(url+'course.html'); assert.match(await p.locator('[data-practice-for="conditions"] .practice-status').innerText(),/已完成/);
  await p.locator('[data-practice-for="conditions"] a').last().click();
  await p.locator('.practice-done input').uncheck(); await p.locator('#mark-read').click();
  s=await state(p); assert.equal(s.lessons.conditions.completed,false); assert.equal(s.lessons.conditions.practiceDone,false);
 });
 await check('A5 export-clear-import roundtrip and namespace',async p=>{
  const s=fresh();s.settings.fontSize=30;s.lessons.conditions={completed:true,practiceDone:true,lastStepId:'s-practice'};
  await seed(p,s); await p.evaluate(()=>localStorage.setItem('unrelated','keep'));
  await p.goto(url+'settings.html'); await p.locator('#export-btn').click();
  const backup=await p.locator('#export-text').inputValue(); assert.deepEqual(JSON.parse(backup),s);
  await p.locator('#clear-btn').click(); await p.waitForLoadState('load');
  assert.equal((await state(p)).settings.fontSize,30); assert.deepEqual((await state(p)).lessons,{});
  assert.equal(await p.evaluate(()=>localStorage.getItem('unrelated')),'keep');
  await p.locator('#import-text').fill(backup); await p.locator('#import-btn').click();
  assert.match(await p.locator('#import-preview').innerText(),/1 节已读/); assert.deepEqual((await state(p)).lessons,{});
  await p.locator('#import-preview button').click(); await p.waitForLoadState('load'); assert.deepEqual(await state(p),s);
  for(const bad of ['{',JSON.stringify({...s,courseId:'other'}),JSON.stringify({...s,schemaVersion:2}),'中'.repeat(44000)]) {
   await p.locator('#import-text').fill(bad); await p.locator('#import-btn').click();
   assert.equal(await p.locator('#import-preview button').count(),0); assert.deepEqual(await state(p),s);
  }
 });
 for(const failure of ['read','initial-write','later-write']) await check('A6 storage '+failure,async(p,c)=>{
  await c.addInitScript(failure=>{
   const orig=Storage.prototype.setItem;
   if(failure==='read') Storage.prototype.getItem=function(){throw Error('blocked read')};
   else Storage.prototype.setItem=function(k,v){if(failure==='initial-write'||k.endsWith(':state'))throw Error('quota');return orig.call(this,k,v)};
  },failure);
  await p.goto(url+'lessons/run-and-bindings.html#s-quiz-1'); await answer(p,'a');
  assert.equal(await p.locator('.step.active .quiz-result').isVisible(),true);assert.equal(await p.locator('#save-banner').isVisible(),true);
  await p.goto(url+'settings.html');if(failure==='later-write')await p.locator('input[value="30"]').check();assert(!/：可用/.test(await p.locator('#storage-status').innerText()));
 });
 await check('A5 failed import/clear preserves old storage and reports failure',async p=>{
  const s=fresh();s.lessons.conditions={completed:true}; await seed(p,s); await p.goto(url+'settings.html');
  await p.evaluate(()=>Storage.prototype.setItem=function(){throw Error('quota')});
  await p.locator('#import-text').fill(JSON.stringify(fresh())); await p.locator('#import-btn').click(); await p.locator('#import-preview button').click();
  assert.deepEqual(await state(p),s); assert.equal(await p.locator('#save-banner').isVisible(),true);
  await p.locator('#clear-btn').click(); assert.deepEqual(await state(p),s);
 });
 for(const raw of ['{bad',JSON.stringify({...fresh(),schemaVersion:9}),'{"__proto__":{},"schemaVersion":1}',JSON.stringify({...fresh(),courseId:'wrong'})]) await check('A6 corrupt state preserved '+raw.slice(0,25),async p=>{
  await seed(p,raw); await p.goto(url+'lessons/run-and-bindings.html#s-quiz-1');await answer(p,'a');
  assert.equal(await p.evaluate(k=>localStorage.getItem(k),KEY),raw);
  await p.goto(url+'settings.html');await p.getByRole('button',{name:'查看原始文本'}).click();assert.equal(await p.locator('.raw-backup').innerText(),raw);
 });
 for(const mode of ['disabled','blocked','init-failure']) await check('A6 static fallback '+mode,async(p,c)=>{
  if(mode==='blocked') await c.route('**/reader.*.js',r=>r.abort());
  if(mode==='init-failure') await c.addInitScript(()=>{Element.prototype.querySelectorAll=new Proxy(Element.prototype.querySelectorAll,{apply(fn,self,args){if(args[0]==='.quiz')throw Error('init');return Reflect.apply(fn,self,args)}})});
  await p.goto(url+'lessons/conditions.html');
  assert.equal(await p.locator('.step:visible').count(),8); assert.equal(await p.locator('.answer-zone:visible').count(),2);
  assert.equal(await p.locator('.quiz-submit:visible').count(),0);assert.equal(await p.locator('.practice-done:visible').count(),0);
  assert.equal(await p.locator('.quiz-option:visible').count(),8);
  assert.equal(await p.locator('.quiz-hint:visible').count(),0);
  assert.equal(await p.locator('.reveal-content:visible').count(),4);
 },mode==='disabled'?{javaScriptEnabled:false}:{});
 await check('A7 revisions and deleted records excluded across home/review/preview',async p=>{
  await p.goto(url+'lessons/run-and-bindings.html');const rev=await qrev(p,'run-and-bindings-q1');
  const s=fresh();s.lessons.deleted={completed:true};s.lastLocation={lessonId:'deleted',stepId:'gone'};
  s.questions['run-and-bindings-q1']={revision:rev+1,attempts:4,wrongAttempts:0,lastOptionId:'b',lastCorrect:true,needsReview:false};
  s.questions.deleted={revision:1,attempts:1,wrongAttempts:1,lastOptionId:'a',lastCorrect:false,needsReview:true};
  await seed(p,s);await p.reload();assert.equal(await p.locator('#stat-read').innerText(),'0');assert.equal(await p.locator('#stat-review').innerText(),'1');
  assert(!/deleted/.test(await p.locator('#home-primary').getAttribute('href')));
  await p.goto(url+'settings.html');await p.locator('#import-text').fill(JSON.stringify(s));await p.locator('#import-btn').click();assert.match(await p.locator('#import-preview').innerText(),/1 道待复习/);
  await p.goto(url+'review.html'); assert.equal(await p.locator('#review-list li').count(),1);assert.match(await p.locator('#review-list').innerText(),/已更新/);
  await p.locator('#review-list a').click();assert.equal(await p.locator('.step.active .quiz-submit').isEnabled(),true);assert.equal(await p.locator('.step.active input:checked').count(),0);
  await answer(p,'b');const record=(await state(p)).questions['run-and-bindings-q1'];assert.equal(record.attempts,1);assert.equal(record.revision,rev);
 });
 await check('A7 current catalog progress and 10-item review pagination',async p=>{
  await p.goto(url+'review.html');const items=await p.locator('#review-index li').evaluateAll(ns=>ns.map(n=>({id:n.dataset.questionId,revision:Number(n.dataset.questionRevision)})));
  assert.equal(items.length,38); const s=fresh();for(const q of items)s.questions[q.id]={revision:q.revision,attempts:1,wrongAttempts:1,lastOptionId:'a',lastCorrect:false,needsReview:true};
  await seed(p,s);await p.goto(url+'review.html');assert.equal(await p.locator('#review-list li').count(),10);
  for(let i=0;i<3;i++)await p.getByRole('button',{name:'下一页',exact:true}).click();assert.equal(await p.locator('#review-list li').count(),8);
  await p.goto(url+'course.html');const lids=await p.locator('li[data-lesson-id]').evaluateAll(ns=>ns.map(n=>n.dataset.lessonId));
  for(const lid of lids)s.lessons[lid]={completed:true};await seed(p,s);await p.reload();assert.equal(await p.locator('#stat-read').innerText(),'19');assert.equal(await p.locator('#home-primary').innerText(),'重新查看课程');
 });
 await check('A7 renamed and reordered catalog retains progress by ID',async(p,c)=>{
  const s=fresh();s.lessons.strings={completed:true,lastStepId:'s-recap'};
  s.lessons.conditions={completed:false,lastStepId:'s-quiz-1'};
  s.lastLocation={lessonId:'conditions',stepId:'s-quiz-1'};
  await seed(p,s);
  // Simulate a newly rendered catalog before reader.js initializes it.
  await c.addInitScript(()=>document.addEventListener('DOMContentLoaded',()=>{
   for(const list of document.querySelectorAll('#lesson-order, .module ul')){
    for(const li of [...list.children].reverse()){
     list.appendChild(li);const a=li.querySelector('a');if(a)a.textContent='重命名 '+li.dataset.lessonId;
    }
   }
  },true));
  await p.goto(url+'index.html');assert.equal(await p.locator('#stat-read').innerText(),'1');
  assert.match(await p.locator('#home-primary').getAttribute('href'),/conditions.html#s-quiz-1$/);
  assert.match(await p.locator('#lesson-order li').first().getAttribute('data-lesson-id'),/tests-boundaries/);
  await p.goto(url+'course.html');
  assert.match(await p.locator('li[data-lesson-id="strings"] a').first().innerText(),/重命名/);
  assert.match(await p.locator('li[data-lesson-id="strings"] .lesson-status').innerText(),/已读/);
  assert.deepEqual(await state(p),s);
 });
 await check('A9 three font sizes persist and code preserves indentation',async p=>{
  for(const size of [22,26,30]){
   await p.goto(url+'settings.html');await p.locator(`input[name="fs"][value="${size}"]`).check();
   await p.goto(url+'lessons/conditions.html#s-predict');
   const layout=await p.evaluate(()=>({body:getComputedStyle(document.body).fontSize,code:getComputedStyle(document.querySelector('.step.active pre')).whiteSpace,button:document.querySelector('#step-nav button').getBoundingClientRect().height}));
   assert.equal(layout.body,size+'px');assert.equal(layout.code,'pre');assert(layout.button>=48);
  }
 });
 await check('A9 all pages/steps at 320/600/800/1024 and font 30',async p=>{
  const s=fresh();s.settings.fontSize=30;await seed(p,s);await p.goto(url+'course.html');
  const urls=await p.locator('li[data-lesson-id] > a:first-child').evaluateAll(ns=>ns.map(n=>n.href));
  for(const width of [320,600,800,1024]){
   await p.setViewportSize({width,height:900});
   for(const target of [url+'index.html',url+'course.html',url+'review.html',url+'settings.html',...urls]){
    await p.goto(target);
    const ids=await p.locator('.step').evaluateAll(ns=>ns.map(n=>n.id));
    for(const id of (ids.length?ids:[null])){
     if(id){await p.evaluate(id=>location.hash=id,id);await active(p,id);}
     for(const b of await p.locator('.step.active .reveal-btn').all())await b.click();
     assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${target}#${id} overflows at ${width}`);
    }
   }
  }
 });
 await check('A11 offline current page, no requests on interactions, keyboard',async(p,c)=>{
  await p.goto(url+'lessons/run-and-bindings.html#s-predict'); const requests=[];p.on('request',r=>requests.push(r.url()));
  await c.setOffline(true); await p.locator('.step.active .reveal-btn').focus();await p.keyboard.press('Enter');
  assert.equal(await p.locator('.step.active .reveal-btn').getAttribute('aria-expanded'),'true');
  await p.getByRole('button',{name:'下一部分',exact:true}).click();await p.getByRole('button',{name:'下一部分',exact:true}).click();
  await p.locator('.step.active input[value="b"]').focus();await p.keyboard.press('Space');
  await p.locator('.step.active .quiz-submit').focus();await p.keyboard.press('Enter');
  assert.equal(await p.locator('.step.active .quiz-result').isVisible(),true);assert.deepEqual(requests,[]);
 });
 await check('A8 all links/resources HTTP and ES5 output semantics',async p=>{
  await p.goto(url+'course.html');const urls=await p.locator('a').evaluateAll(ns=>ns.map(n=>n.href));
  for(const u of new Set(urls)){const res=await p.request.get(u);assert.equal(res.status(),200,u);}
  await p.goto(url+'lessons/conditions.html');const asset=await p.locator('script[src]').getAttribute('src');
  const delivered=await (await p.request.get(new URL(asset,url).href)).text();
  const source=fs.readFileSync(path.join(__dirname,'../assets/reader.js'),'utf8');
  const clean=s=>JSON.parse(JSON.stringify(acorn.parse(s,{ecmaVersion:5}), (k,v)=>['start','end'].includes(k)?undefined:v));
  assert.deepEqual(clean(delivered),clean(source));
  const css=await p.locator('link[rel="stylesheet"]').getAttribute('href');assert.equal((await p.request.get(new URL(css,url).href)).status(),200);
 });
 await browser.close();console.log(JSON.stringify(results));
})().catch(async e=>{if(browser)await browser.close();console.error(e);process.exitCode=1});
