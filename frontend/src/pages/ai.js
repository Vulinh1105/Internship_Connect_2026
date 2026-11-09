import {api,stream} from '../api/client.js';
import {esc,tags,box,copy,empty,money,heading,field,area,select,link,btn,form,grid,status,toast,bindForm,action} from '../components/ui.js';
import {jobCard,loginRequired} from './public.js';
import {interviewer,interviewMedia} from '../components/interviewer.js?v=company-interview-1';

const key=user=>'ic-chat-'+user.id;
function compareTable(jobs){
  const rows=[['Vị trí',j=>j.title],['Địa điểm',j=>j.location],['Phụ cấp',j=>money(j.salary_min,j.salary_max)],
    ['Yêu cầu',j=>j.requirements],['Quyền lợi',j=>j.details?.benefits||''],['Độ phù hợp',j=>j.match_score==null?'':j.match_score+'%']];
  return '<div class="scroll"><table><thead><tr><th>Tiêu chí</th>'+jobs.map(j=>'<th>'+esc(j.company_name)+'</th>').join('')
    +'</tr></thead><tbody>'+rows.map(([name,get])=>'<tr><th scope="row">'+esc(name)+'</th>'
      +jobs.map(j=>'<td>'+esc(get(j))+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';
}
function messageExtras(container,data){
  container.innerHTML=(data.jobs?.length?(data.intent==='compare'?compareTable(data.jobs):grid(data.jobs.map(jobCard))):'')
    +(data.sources?.length?'<p class="muted">'+data.sources.map(s=>'['+s.number+'] '+esc(s.title)+' ('+esc(s.source)+')').join(' · ')+'</p>':'')
    +(data.action==='start_mock_interview'?link('mock','Luyện phỏng vấn'):'')
    +(data.id?'<div class="row">'+btn('good','Hữu ích',data.id)+btn('bad','Chưa hữu ích',data.id)+'</div>':'');
  for(const [name,rating] of [['good',1],['bad',-1]])action(container,name,async id=>{
    await api('/chat/messages/'+id+'/feedback',{method:'POST',data:{rating}});toast('Đã ghi nhận phản hồi');
  });
}
function bubble(log,role,text,data){
  const node=document.createElement('div');
  node.className='bubble '+role;
  const content=document.createElement('div');
  content.textContent=text;
  node.append(content);
  if(data){
    const extras=document.createElement('div');
    node.append(extras);
    messageExtras(extras,data);
  }
  log.append(node);log.scrollTop=log.scrollHeight;
  return [content,node];
}
async function chat({root,user,reload}){
  if(!user)return loginRequired(root);
  const stored=sessionStorage.getItem(key(user));
  let id=Number(stored), history=[];
  if(id){
    try{history=await api('/chat/sessions/'+id+'/messages');}
    catch{sessionStorage.removeItem(key(user));id=0;}
  }
  root.innerHTML='<section class="chat-layout" aria-labelledby="chat-title">'
    +'<div class="chat-toolbar"><button type="button" class="secondary" data-action="toggle-history" aria-controls="chat-sidebar" aria-expanded="false">Lịch sử</button>'
    +'<h1 id="chat-title">Chatbot thực tập</h1>'+btn('new-chat','Hội thoại mới')+'</div>'
    +'<aside class="chat-sidebar" id="chat-sidebar" aria-labelledby="chat-history-title" hidden>'
    +'<h2 id="chat-history-title">Lịch sử hội thoại</h2><div id="chat-history"></div>'+btn('more-chat','Xem thêm')+'</aside>'
    +'<div class="chat-conversation"><div class="chat-log" aria-live="polite"></div>'
    +form('chat',field('message','Câu hỏi','','text','required minlength="2" maxlength="500" placeholder="Nhập câu hỏi…"'),'Gửi')
    +'</div></section>';
  const sidebar=root.querySelector('#chat-sidebar');
  const historyToggle=root.querySelector('[data-action="toggle-history"]');
  const narrow=matchMedia('(max-width: 680px)');
  const sidebarKey=key(user)+'-sidebar';
  function showHistory(open){
    sidebar.hidden=!open;
    historyToggle.setAttribute('aria-expanded',String(open));
  }
  showHistory(!narrow.matches&&sessionStorage.getItem(sidebarKey)!=='closed');
  historyToggle.addEventListener('click',()=>{
    showHistory(sidebar.hidden);
    if(!narrow.matches)sessionStorage.setItem(sidebarKey,sidebar.hidden?'closed':'open');
  });
  root.addEventListener('keydown',event=>{
    if(event.key==='Escape'&&!sidebar.hidden){
      showHistory(false);
      if(!narrow.matches)sessionStorage.setItem(sidebarKey,'closed');
      historyToggle.focus();
    }
  });
  const list=root.querySelector('#chat-history');
  const more=root.querySelector('[data-action="more-chat"]');
  let before=null;
  async function loadHistory(append=false){
    const page=await api('/chat/sessions'+(append?'?before='+before:''));
    const entries=page.items.map(s=>btn('open-chat',s.title,s.id)).join('');
    if(append)list.insertAdjacentHTML('beforeend',entries);
    else list.innerHTML=entries||'<span class="muted">Chưa có hội thoại.</span>';
    before=page.next;
    more.hidden=!before;
    for(const button of list.querySelectorAll('[data-action="open-chat"]')){
      button.setAttribute('aria-pressed',String(Number(button.dataset.value)===id));
    }
  }
  list.addEventListener('click',async event=>{
    const button=event.target.closest('[data-action="open-chat"]');
    if(button){
      sessionStorage.setItem(key(user),button.dataset.value);
      await reload();
    }
  });
  action(root,'more-chat',()=>loadHistory(true));
  await loadHistory();
  const log=root.querySelector('.chat-log');
  if(!history.length)bubble(log,'assistant','Chào bạn! Ví dụ, hãy hỏi “Điều kiện công khai tin là gì?” hoặc “Đơn ứng tuyển của tôi đang ở đâu?”.');
  for(const m of history)bubble(log,m.role,m.text,m.role==='assistant'?{...m.meta,id:m.id}:null);
  action(root,'new-chat',async()=>{sessionStorage.removeItem(key(user));await reload();});
  bindForm(root,'chat',async(data,el)=>{
    if(!id){id=(await api('/chat/sessions',{method:'POST'})).id;sessionStorage.setItem(key(user),id);}
    bubble(log,'user',data.message);
    el.reset();
    const [content,node]=bubble(log,'assistant','Đang xử lý…');
    try{
      let text='';
      await stream(await api('/chat/sessions/'+id+'/messages',{method:'POST',data:{message:data.message}}),(kind,result)=>{
        if(kind==='delta'){text+=result.text;content.textContent=text;}
        if(kind==='result'){
          content.textContent=result.answer;
          const extras=document.createElement('div');node.append(extras);messageExtras(extras,result);
        }
        log.scrollTop=log.scrollHeight;
      });
    }catch(error){content.textContent=error.message;}
    await loadHistory();
  });
}
const searchKey=text=>text.toLocaleLowerCase('vi').normalize('NFD').replace(/\p{M}/gu,'').replace(/đ/g,'d')
  .replace(/[^\p{L}\p{N}]+/gu,' ').trim();

function interviewSuggestions(root,name,options,onPick,onEdit){
  const input=root.querySelector('[name="'+name+'"]');
  const list=root.querySelector('[data-suggestions="'+name+'"]');
  input.addEventListener('input',()=>{
    onEdit();
    const query=searchKey(input.value);
    const matches=query?options.filter(([,label])=>{
      const key=searchKey(label);
      return key.includes(query)||key.replaceAll(' ','').includes(query.replaceAll(' ',''));
    }):[];
    list.innerHTML=matches.map(([id,label])=>btn('suggest',label,id)).join('');
    action(list,'suggest',id=>{
      const [key,label]=options.find(([key])=>String(key)===id);
      input.value=label;
      list.replaceChildren();
      onPick(key);
    });
  });
}

async function mock({root,user}){
  if(!user)return loginRequired(root);
  const [roles,history,catalog]=await Promise.all([api('/mock-interviews/roles'),api('/mock-interviews'),api('/mock-interviews/question-sets/catalog')]);
  const companyChoices=[...new Map(catalog.map(s=>[s.company_id,s.company_name]))];
  root.innerHTML=heading('Phỏng vấn ảo','Câu trả lời đã lọc thông tin liên hệ được gửi tới OpenAI để đặt câu hỏi và chấm điểm cuối buổi.')
    +box('<h2>Luyện theo doanh nghiệp</h2>'+(catalog.length?form('start-company',field('company','Tìm doanh nghiệp','','search','placeholder="Ví dụ: FPT" autocomplete="off"')
      +'<div class="row" data-suggestions="company"></div><div id="company-set-choices" class="stack"></div>','Bắt đầu phỏng vấn'):empty('Chưa có bộ câu hỏi doanh nghiệp đang công khai.')))
    +box('<h2>Luyện theo vai trò</h2>'+form('start',select('role','Vị trí',roles,roles.includes('Backend Intern')?'Backend Intern':roles[0])
      +select('level','Cấp độ',[['intern','Thực tập'],['fresher','Fresher'],['junior','Junior']]),'Bắt đầu phỏng vấn'))
    +'<h2>Buổi luyện gần đây</h2>'+grid(history.map(s=>box('<h3>'+esc(s.role)+'</h3>'+tags(s.source?.company_name,s.source?.title,s.state==='evaluating'?'Đang chấm':status(s.state),s.report&&s.report.score+' / 100')
      +link('mock-session/'+s.id,s.state==='active'?'Tiếp tục':'Xem buổi luyện'))));
  if(catalog.length){
    const choices=root.querySelector('#company-set-choices');
    const start=root.querySelector('#start-company button:not([type])');
    const labels={basic:'Cơ bản',intermediate:'Trung bình',advanced:'Nâng cao'};
    let available=[];
    function clearPosition(){
      available=[];
      start.disabled=true;
      choices.querySelector('#position-sets')?.replaceChildren();
    }
    function showSets(sets){
      available=sets;
      const section=choices.querySelector('#position-sets');
      section.innerHTML=select('question_set_id','Bộ câu hỏi',sets.map(s=>[s.id,s.title]))+'<div id="set-preview"></div>';
      const selected=section.querySelector('[name="question_set_id"]');
      function preview(){
        const set=sets.find(s=>s.id===Number(selected.value));
        section.querySelector('#set-preview').innerHTML=tags(set.job_category,set.question_count+' câu',
          set.difficulties.map(d=>labels[d]||d).join(' / '),set.estimated_seconds/60+' phút tối đa cho các câu chính')
          +copy(set.description)+(set.job_id?link('job/'+set.job_id,'Xem chi tiết vị trí'):'');
      }
      selected.addEventListener('change',preview);
      preview();
      start.disabled=false;
    }
    function showPositions(companyId){
      const sets=catalog.filter(s=>s.company_id===Number(companyId));
      const hiring=[...new Map(sets.filter(s=>s.job_id).map(s=>[s.job_id,s.job_title]))];
      const practice=sets.filter(s=>!s.job_id);
      const extra=[...new Map(practice.map(s=>[searchKey(s.job_title),s.job_title]))];
      choices.innerHTML=field('position','Tìm vị trí đang tuyển','','search','placeholder="Ví dụ: AI Engineer" autocomplete="off"')
        +'<div class="row" data-suggestions="position"></div>'
        +(extra.length?'<details><summary>Vị trí luyện tập chưa đăng tin</summary><div id="practice-positions" class="row">'
          +extra.map(([key,title])=>btn('practice-position',title,key)).join('')+'</div></details>':'')
        +'<div id="position-sets" class="stack"></div>';
      interviewSuggestions(choices,'position',hiring,id=>showSets(sets.filter(s=>s.job_id===id)),clearPosition);
      action(choices,'practice-position',key=>{
        choices.querySelector('[name="position"]').value='';
        choices.querySelector('[data-suggestions="position"]').replaceChildren();
        showSets(practice.filter(s=>searchKey(s.job_title)===key));
      });
      choices.querySelector('[name="position"]').focus();
    }
    start.disabled=true;
    interviewSuggestions(root,'company',companyChoices,showPositions,()=>{
      clearPosition();
      choices.replaceChildren();
    });
    bindForm(root,'start-company',async data=>{
      const id=Number(data.question_set_id);
      if(!available.some(set=>set.id===id))throw new Error('Hãy chọn doanh nghiệp, vị trí và bộ câu hỏi.');
      const session=await api('/mock-interviews',{method:'POST',data:{question_set_id:id}});
      location.hash='mock-session/'+session.id+'/start';
    });
  }
  bindForm(root,'start',async data=>{const s=await api('/mock-interviews',{method:'POST',data:{role:data.role,level:data.level}});location.hash='mock-session/'+s.id+'/start';});
}
function reportView(r){
  if(r.domains){
    const names={knowledge:'Kiến thức chuyên môn',problem_solving:'Giải quyết vấn đề'};
    const remarks=(title,items)=>'<h3>'+title+'</h3>'+(items.length?'<ul>'+items.map(x=>'<li>'+esc(x.text)
      +' <small>(Lượt '+esc(x.turn_ids.join(', '))+')</small></li>').join('')+'</ul>':empty('Chưa có nhận xét có dẫn chứng.'));
    return '<h2>Kết quả phỏng vấn</h2>'+tags('Tổng thể '+r.score+' / 100',r.band,r.previous_score!=null?'Buổi trước '+r.previous_score:'')
      +Object.entries(r.domains).map(([key,d])=>box('<h3>'+names[key]+' · '+d.score+' / 100</h3>'+tags(d.band)
        +(d.question_count?'<ul>'+d.criteria.map(c=>'<li>'+esc(c.label)+' · '+c.score+' / 25</li>').join('')+'</ul>'
          :copy('Chưa có lượt trả lời thuộc tiêu chí này.')))).join('')
      +remarks('Điểm mạnh',r.strengths)+remarks('Hạn chế',r.limitations)
      +(r.practice.length?'<h3>Gợi ý luyện tập</h3><ul>'+r.practice.map(t=>'<li>'+esc(t)+'</li>').join('')+'</ul>':'')
      +'<details><summary>Lịch sử và bằng chứng chấm điểm</summary>'+r.answers.map(a=>box('<h3>Lượt '+a.turn_id+' · '+esc(a.question)+'</h3>'
        +(a.skipped?copy(a.timed_out?'Hết giờ':'Đã bỏ qua'):copy(a.transcript))
        +a.results.map(x=>'<h4>'+names[x.domain]+' · '+x.scores.reduce((a,b)=>a+b,0)*2.5+' / 100</h4>'
          +(x.quote?copy('“'+x.quote+'”'):'')+copy(x.feedback)).join(''))).join('')+'</details>';
  }
  return '<h2>Kết quả luyện tập</h2>'+tags(r.score+' / 100',r.previous_score!=null?'Buổi trước '+r.previous_score:'',r.delta!=null?'Thay đổi '+r.delta:'')
    +'<ul>'+r.practice.map(s=>'<li>'+esc(s)+'</li>').join('')+'</ul>'
    +(r.example?'<h3>Câu trả lời mẫu</h3>'+copy(r.example):'')
    +(r.gaps?.length?'<h3>Tiêu chí cần luyện thêm</h3>'+tags(...r.gaps.map(c=>c.criterion)):'')
    +r.answers.map(a=>box('<h3>'+esc(a.question)+'</h3>'+tags(a.skipped?'Đã bỏ qua':a.score+' / 100')+copy(a.transcript)
      +'<ul>'+a.criteria.map(c=>'<li><b>'+esc(c.criterion)+'</b> · '+c.score+'/2'+(c.quote?copy('“'+c.quote+'”'):'')+copy(c.feedback)+'</li>').join('')+'</ul>')).join('');
}
async function mockSession({root,user,args,signal}){
  if(!user)return loginRequired(root);
  const endpoint='/mock-interviews/'+Number(args[0]);
  let session=await api(endpoint,{signal});
  if(signal.aborted)return;
  root.innerHTML=heading(session.source?.job_title||session.role,session.source
    ?session.source.company_name+' · '+session.source.title
    :'Interview AI đặt câu hỏi. Evaluation AI chấm toàn bộ lịch sử khi buổi phỏng vấn kết thúc.')
    +link('mock','Buổi luyện của bạn')
    +'<div class="interview-layout">'+interviewer+'<div class="interview-question"></div></div>';
  const panel=root.querySelector('.interview-question');
  let state='ready', deadline=0, retryAt=0;
  function updateControls(next){
    state=next;
    const mic=panel.querySelector('[data-action="mic"]');
    const read=panel.querySelector('[data-action="read"]');
    if(mic){
      mic.textContent=state==='listening'?'Dừng micro':'Bật micro';
      mic.disabled=state==='thinking';
    }
    if(read)read.disabled=['thinking','listening'].includes(state);
    for(const button of panel.querySelectorAll('#answer button, #audio button, [data-action="skip"], [data-action="finish"]')){
      button.disabled=['thinking','listening'].includes(state);
    }
  }
  const media=interviewMedia(root.querySelector('.interviewer'),{
    endpoint, mode:session.mode, signal, onError:toast, onState:updateControls,
    remainingMs:()=>Math.max(0,deadline-performance.now()),
    onTranscript(text){
      const input=panel.querySelector('[name="transcript"]');
      if(!input)return;
      input.value=text.slice(0,5000);
      panel.querySelector('[name="confirmed"]').checked=false;
      input.focus();
    },
  });
  let autoRead=true;
  function render(){
    if(!session.question){
      media.set('finished');
      panel.innerHTML=box(session.report?reportView(session.report):empty('Buổi phỏng vấn đã kết thúc.')
        +(session.evaluation_pending?'<p role="status" id="evaluation-status"></p>'+btn('evaluate','Chấm điểm hoặc tải lại kết quả'):''));
      action(panel,'evaluate',evaluate);
      return;
    }
    deadline=performance.now()+session.remaining_ms;
    panel.innerHTML=box(tags('Câu '+(session.cursor+1)+' / '+session.total,session.turn?'Câu hỏi bổ sung':'')+'<p><strong>Thời gian còn lại <time id="question-timer">10:00</time></strong></p>'
      +'<h2>'+esc(session.question.question)+'</h2><div class="row">'+btn('read','Đọc câu hỏi')+btn('mic','Bật micro')+btn('skip','Bỏ qua')+btn('finish','Kết thúc và chấm điểm')+'</div>'
      +'<label><input type="checkbox" name="auto_read" '+(autoRead?'checked':'')+'> Tự đọc câu hỏi tiếp theo</label>'
      +form('answer',area('transcript','Câu trả lời','','required maxlength="5000"')
        +'<label><input type="checkbox" name="confirmed" required> Tôi đã kiểm tra và xác nhận câu trả lời</label>','Gửi câu trả lời')
      +(session.mode==='openai'?'<details><summary>Tải bản ghi âm có sẵn</summary>'
        +form('audio','<label class="field">Tệp âm thanh<input type="file" name="file" required accept="audio/*"></label>'
          +'<label><input type="checkbox" name="consent" value="true" required> Đồng ý gửi âm thanh tới OpenAI để chuyển thành văn bản</label>','Chuyển thành văn bản')+'</details>':''));
    panel.querySelector('[name="auto_read"]').addEventListener('change',event=>{autoRead=event.target.checked;});
    bindForm(panel,'answer',data=>submit({transcript:data.transcript,confirmed:!!data.confirmed}));
    bindForm(panel,'audio',data=>media.transcribe(data),{keepFiles:true});
    action(panel,'skip',async()=>{if(confirm('Bỏ qua câu này?'))await submit({skip:true});});
    action(panel,'finish',async()=>{
      if(['listening','thinking'].includes(state) || !confirm('Kết thúc và chấm theo các lượt đã gửi?'))return;
      media.stopSpeech();
      media.set('thinking');
      try{
        session=await api(endpoint+'/finish',{method:'POST',signal});
        if(!signal.aborted){
          render();
          await evaluate();
        }
      }finally{
        if(!signal.aborted&&session.question)media.set('ready');
      }
    });
    action(panel,'read',()=>media.play(session.question.question));
    action(panel,'mic',()=>media.listen());
    media.set('ready');
    paintTime();
  }
  function paintTime(){
    const clock=panel.querySelector('#question-timer');
    if(!clock)return 0;
    const seconds=Math.max(0,Math.ceil((deadline-performance.now())/1000));
    clock.textContent=String(Math.floor(seconds/60)).padStart(2,'0')+':'+String(seconds%60).padStart(2,'0');
    return seconds;
  }
  async function tick(){
    if(!session.question||signal.aborted||paintTime()||state==='thinking'||performance.now()<retryAt)return;
    media.stopSpeech();
    media.stopInput();
    media.set('thinking','Đã hết thời gian trả lời');
    try{
      session=await api(endpoint+'/timeout',{method:'POST',signal,data:{cursor:session.cursor,turn:session.turn}});
      if(signal.aborted)return;
      render();
      if(session.evaluation_pending)await evaluate();
      else if(autoRead&&session.question)void media.play(session.question.question);
    }catch(error){
      if(signal.aborted)return;
      retryAt=performance.now()+3000;
      try{session=await api(endpoint,{signal});if(!signal.aborted)render();}
      catch{if(!signal.aborted)media.set('ready');}
    }
  }
  let evaluationRunning=false;
  async function evaluate(){
    if(!session.evaluation_pending||evaluationRunning||signal.aborted)return;
    const retryable=[
      'AI chưa trả đủ điểm và dẫn chứng cho lịch sử phỏng vấn. Hãy thử chấm lại.',
      'Buổi phỏng vấn đang được chấm. Hãy tải lại sau.',
      'Trạng thái chấm điểm vừa thay đổi. Hãy tải lại.',
      'Lượt chấm vừa thay đổi. Hãy tải lại báo cáo.',
    ];
    evaluationRunning=true;
    panel.innerHTML=box('<p role="status">Đang chấm…</p>');
    let delay=2000;
    try{
      while(!signal.aborted){
        try{
          session=await api(endpoint+'/evaluation',{method:'POST',signal});
          if(!signal.aborted)render();
          return;
        }catch(error){
          if(signal.aborted)return;
          if(!retryable.includes(error.message)){
            render();
            panel.querySelector('#evaluation-status').textContent=error.message;
            return;
          }
        }
        await new Promise(resolve=>setTimeout(resolve,delay));
        delay=Math.min(delay*2,20000);
      }
    }finally{
      evaluationRunning=false;
    }
  }
  async function submit(data){
    if(['listening','thinking'].includes(state))return;
    if(!paintTime()){await tick();return;}
    media.stopSpeech();
    media.set('thinking','Đang chuẩn bị câu hỏi tiếp theo');
    try{
      session=await api(endpoint+'/answers',{method:'POST',signal,data:{...data,cursor:session.cursor,turn:session.turn}});
      if(signal.aborted)return;
      render();
      if(session.evaluation_pending)await evaluate();
      else if(autoRead && session.question)void media.play(session.question.question);
    }catch(error){
      if(signal.aborted)return;
      media.set('ready');
      throw error;
    }
  }
  render();
  if(session.evaluation_pending)void evaluate();
  const ticker=setInterval(()=>void tick(),250);
  signal.addEventListener('abort',()=>clearInterval(ticker),{once:true});
  if(args[1]==='start'&&session.question){
    requestAnimationFrame(()=>{if(autoRead&&!signal.aborted&&state==='ready')void media.play(session.question.question);});
  }
}
export const pages={chat,mock,'mock-session':mockSession};
