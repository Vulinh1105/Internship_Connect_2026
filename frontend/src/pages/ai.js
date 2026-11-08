import {api,stream} from '../api/client.js';
import {esc,tags,box,copy,empty,money,heading,field,area,select,link,btn,form,grid,status,toast,bindForm,action} from '../components/ui.js';
import {jobCard,loginRequired} from './public.js';
import {interviewer,interviewMedia} from '../components/interviewer.js?v=interview-avatar-2';

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
  const sessionList='<details open><summary>Lịch sử hội thoại</summary><div class="row" id="chat-history"></div>'
    +btn('more-chat','Xem thêm')+'</details>';
  root.innerHTML=heading('Chatbot thực tập','Tìm vị trí, hỏi quy trình, tra cứu đơn của bạn hoặc luyện phỏng vấn.')
    +box('<div class="row">'+btn('new-chat','Hội thoại mới')+'</div>'+sessionList+'<div class="chat-log" aria-live="polite"></div>'
    +form('chat',field('message','Câu hỏi','','text','required minlength="2" maxlength="500"'),'Gửi'));
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
async function mock({root,user}){
  if(!user)return loginRequired(root);
  const [roles,history]=await Promise.all([api('/mock-interviews/roles'),api('/mock-interviews')]);
  root.innerHTML=heading('Phỏng vấn ảo','Luyện câu hỏi theo vai trò, xem dẫn chứng và theo dõi tiến bộ.')
    +box(form('start',select('role','Vị trí',roles,roles.includes('Backend Intern')?'Backend Intern':roles[0])
      +select('level','Cấp độ',[['intern','Thực tập'],['fresher','Fresher'],['junior','Junior']]),'Bắt đầu phỏng vấn'))
    +'<h2>Buổi luyện gần đây</h2>'+grid(history.map(s=>box('<h3>'+esc(s.role)+'</h3>'+tags(status(s.state),s.report&&s.report.score+' / 100')
      +link('mock-session/'+s.id,s.state==='active'?'Tiếp tục':'Xem buổi luyện'))));
  bindForm(root,'start',async data=>{const s=await api('/mock-interviews',{method:'POST',data:{role:data.role,level:data.level}});location.hash='mock-session/'+s.id+'/start';});
}
function reportView(r){
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
  root.innerHTML=heading(session.role,'Phỏng vấn ảo · '+(session.mode==='local'?'Chấm thử bằng quy tắc local':'Chấm thử có hỗ trợ mô hình'))
    +link('mock','Buổi luyện của bạn')
    +'<div class="interview-layout">'+interviewer+'<div class="interview-question"></div></div>';
  const panel=root.querySelector('.interview-question');
  let state='ready';
  function updateControls(next){
    state=next;
    const mic=panel.querySelector('[data-action="mic"]');
    const read=panel.querySelector('[data-action="read"]');
    if(mic){
      mic.textContent=state==='listening'?'Dừng micro':'Bật micro';
      mic.disabled=state==='thinking';
    }
    if(read)read.disabled=['thinking','listening'].includes(state);
    for(const button of panel.querySelectorAll('#answer button, #audio button, [data-action="skip"], [data-action="abandon"]')){
      button.disabled=['thinking','listening'].includes(state);
    }
  }
  const media=interviewMedia(root.querySelector('.interviewer'),{
    endpoint, mode:session.mode, signal, onError:toast, onState:updateControls,
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
      panel.innerHTML=box(session.report?reportView(session.report):empty('Buổi luyện đã kết thúc.'));
      return;
    }
    const feedback=session.evaluation;
    const summary=feedback&&!feedback.skipped
      ?'<details class="interview-feedback" open><summary>Câu vừa trả lời · '+esc(feedback.score)+' / 100</summary>'
        +'<ul>'+feedback.criteria.map(item=>'<li><strong>'+esc(item.criterion)+'</strong> · '+esc(item.feedback)+'</li>').join('')+'</ul></details>':'';
    panel.innerHTML=box(summary+tags('Câu '+(session.cursor+1)+' / '+session.total,session.turn?'Câu hỏi bổ sung':'',session.question.seconds+' giây gợi ý')
      +'<h2>'+esc(session.question.question)+'</h2><div class="row">'+btn('read','Đọc câu hỏi')+btn('mic','Bật micro')+btn('skip','Bỏ qua')+btn('abandon','Dừng buổi luyện')+'</div>'
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
    action(panel,'abandon',async()=>{
      if(['listening','thinking'].includes(state) || !confirm('Dừng buổi luyện này?'))return;
      media.stopSpeech();
      media.set('thinking');
      try{
        session=await api(endpoint+'/abandon',{method:'POST',signal});
        if(!signal.aborted)render();
      }finally{
        if(!signal.aborted&&session.question)media.set('ready');
      }
    });
    action(panel,'read',()=>media.play(session.question.question));
    action(panel,'mic',()=>media.listen());
    media.set('ready');
  }
  async function submit(data){
    if(['listening','thinking'].includes(state))return;
    media.stopSpeech();
    media.set('thinking','Đang chấm câu trả lời');
    try{
      session=await api(endpoint+'/answers',{method:'POST',signal,data:{...data,cursor:session.cursor,turn:session.turn}});
      if(signal.aborted)return;
      render();
      if(autoRead && session.question) void media.play(session.question.question);
    }catch(error){
      if(signal.aborted)return;
      media.set('ready');
      throw error;
    }
  }
  render();
  if(args[1]==='start'&&session.question){
    requestAnimationFrame(()=>{if(autoRead&&!signal.aborted&&state==='ready')void media.play(session.question.question);});
  }
}
export const pages={chat,mock,'mock-session':mockSession};
