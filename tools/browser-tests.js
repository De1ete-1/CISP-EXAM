/* Run only in a disposable browser profile on the local preview. Restores all state. */
(async function () {
  const originalState=state,originalView=view,originalStorage=localStorage.getItem(STORAGE_KEY);
  const realNow=Date.now;
  const results=[];
  function check(name,condition){results.push({name,passed:Boolean(condition)});if(!condition)throw new Error(name);}
  function click(selector){const el=document.querySelector(selector);if(!el)throw new Error('Missing '+selector);el.click();}
  try {
    state=defaultState();view='home';render();
    check('522 complete questions',BANK.length===522&&BANK.every((q,i)=>q.id===i+1&&q.options.length===4&&q.options.every(Boolean)&&letters.includes(q.answer)&&q.explanation.length>8));
    check('39 figures / answer figure hidden from exam',BANK.reduce((n,q)=>n+q.images.length,0)===39&&BY_ID.get(233).images[0].role==='explanation');
    const sampled=new Set();let valid=true;
    for(let i=0;i<1000;i++){const ids=randomSample(BANK.map(q=>q.id),100);valid&&=ids.length===100&&new Set(ids).size===100&&ids.every(id=>BY_ID.has(id));ids.forEach(id=>sampled.add(id));}
    check('1000 independent samples have 100 unique valid IDs',valid);
    check('all 522 IDs selectable across samples',sampled.size===522);
    click('[data-action="start"]');
    check('start button creates 120-minute 100-question exam',view==='exam'&&validExam(state.active)&&state.active.deadline-state.active.startedAt===7200000);
    check('exam hides answers and explanations',!document.querySelector('.explanation')&&!document.querySelector('.option.correct')&&document.querySelectorAll('[role="radio"]').length===4);
    const examId=state.active.id,ids=[...state.active.ids],first=ids[0];
    click('[data-answer="B"]');click('[data-action="flag"]');
    check('radio answer and flag handlers',state.active.answers[first]==='B'&&state.active.flags.includes(first)&&document.querySelector('[data-answer="B"]').getAttribute('aria-checked')==='true');
    click('[data-action="next"]');click('[data-action="prev"]');
    check('navigation preserves answers',state.active.current===0&&state.active.answers[first]==='B');
    state=load();
    check('saved exam restores exact deck, answer, flag and deadline',state.active.id===examId&&JSON.stringify(state.active.ids)===JSON.stringify(ids)&&state.active.answers[first]==='B'&&state.active.flags.includes(first));
    click('[data-action="clear-answer"]');
    check('clear answer updates saved progress',!state.active.answers[first]&&answered(state.active)===0);
    click('[data-action="submit"]');
    check('submit confirmation includes unanswered count',$('dialog').open&&$('dialog-description').textContent.includes('100'));
    click('#dialog-cancel');
    check('cancel preserves active exam',state.active&&state.active.id===examId);
    for(const boundary of [0,69,70,71,100]){
      state=defaultState();makeExam();
      state.active.ids.forEach((id,i)=>{const q=BY_ID.get(id);state.active.answers[id]=i<boundary?q.answer:letters.find(l=>l!==q.answer);});
      click('[data-action="submit"]');click('#dialog-confirm');
      check('score boundary '+boundary,score(currentRecord)===boundary&&!state.active&&state.history.length===1);
      check('pass threshold '+boundary,Boolean(document.querySelector('.result-hero.failed'))===(boundary<70));
      check('review and wrong-book totals '+boundary,filteredReview().length===100-boundary&&wrongEntries().length===100-boundary);
    }
    state=defaultState();makeExam();submitExam();
    check('all unanswered scores zero and collects 100 wrongs',score(currentRecord)===0&&answered(currentRecord)===0&&wrongEntries().length===100);
    check('wrong review shows answer, explanation and source',document.querySelector('.answer-summary').textContent.includes('未作答')&&document.querySelector('.explanation p').textContent.length>8&&document.querySelector('.source-line a').href.includes('.pdf'));
    click('[data-action="review-next"]');
    check('review next navigates',reviewIndex===1);
    click('[data-action="review-filter"][data-filter="all"]');
    check('all-question review available',filteredReview().length===100);
    libraryQuery='no-such-query';libraryVolume='6';go('wrong');
    check('wrong navigation resets library filters',libraryQuery===''&&libraryVolume==='all'&&libraryPool().length===100);
    const wrongId=libraryId;
    click('[data-answer="A"]');click('[data-action="reveal"]');
    check('wrong self-test reveals reasoning',reveal&&document.querySelector('.explanation p'));
    click('[data-action="master"]');
    check('mastering removes question from pending book',state.wrong[wrongId].mastered&&pendingWrong().length===99&&wrongEntries().length===100);
    go('library');const input=$('library-search');input.value='#522';input.dispatchEvent(new Event('input',{bubbles:true}));
    check('search by original question number',libraryId===522&&libraryPool().length===1&&document.querySelector('.q-figure'));
    click('[data-action="reveal"]');
    check('diagram question and explanation render',document.querySelector('.q-figure').src.startsWith('data:image/webp;')&&document.querySelector('.explanation p').textContent.includes('网关'));
    go('home');state.active=null;makeExam();const expiredId=state.active.id,deadline=state.active.deadline;Date.now=()=>deadline+100;tick();Date.now=realNow;
    check('deadline automatically submits once',!state.active&&currentRecord.id===expiredId&&currentRecord.timeout&&currentRecord.finishedAt===deadline);
    tick();check('timeout is not duplicated',state.history.filter(r=>r.id===expiredId).length===1);
    const before=JSON.stringify(state);const set=Storage.prototype.setItem;
    try{Storage.prototype.setItem=function(){throw new Error('quota test');};persist();check('storage failure has visible warning and preserves exam state',!storageAvailable&&$('storage-alert').textContent.includes('未能')&&JSON.stringify(state)===before);}finally{Storage.prototype.setItem=set;persist();}
    const countBefore=state.history.length;state.active=null;makeExam();const firstId=state.active.ids[0];state.active.answers[firstId]='D';state.active.flags=[firstId];state.active.current=17;persist();
    check('reload fixture valid',validExam(state.active));
    check('zero horizontal overflow',document.documentElement.scrollWidth<=innerWidth);
    return {passed:results.filter(x=>x.passed).length,total:results.length,results,viewport:[innerWidth,innerHeight]};
  }catch(error){return {error:error.message,results};}
  finally{Date.now=realNow;state=originalState;view=originalView;currentRecord=null;libraryQuery='';libraryVolume='all';reveal=false;studyAnswer=null;storageAvailable=true;if($('dialog').open)$('dialog').close();if(originalStorage===null)localStorage.removeItem(STORAGE_KEY);else localStorage.setItem(STORAGE_KEY,originalStorage);storageWarning();render();}
})();
