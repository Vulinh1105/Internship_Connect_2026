import {api} from '../api/client.js';
import {esc,tags,box,copy,empty,heading,field,area,select,link,btn,form,modes,list,money,status,toast,bindForm,action} from '../components/ui.js';
import {loginRequired} from './public.js';
import {logoTile} from '../components/media.js';

const educations=[['','Chưa nêu'],'Không yêu cầu','Sinh viên đại học/cao đẳng','Sinh viên năm cuối','Mới tốt nghiệp','Trung cấp trở lên','Cao đẳng trở lên','Đại học trở lên','Thạc sĩ trở lên'];
const part=(title,html)=>'<section class="form-section"><h3>'+title+'</h3>'+html+'</section>';
const wide=html=>'<div class="wide">'+html+'</div>';
function jobFields(companies,j={}){
  const d=j.details||{};
  const schedules=[['','Chưa chọn'],['part_time','Bán thời gian'],['full_time','Toàn thời gian']];
  const levels=[['intern','Thực tập'],['fresher','Fresher'],['junior','Junior'],['senior','Senior']];
  return part('1. Thông tin chung','<div class="form-grid">'+select('company_id','Doanh nghiệp',companies.map(c=>[c.id,c.name]),j.company_id)
      +select('level','Cấp độ',levels,j.level)+wide(field('title','Tiêu đề',j.title,'text','required'))
      +field('category','Ngành',j.category,'text','required')+'</div>')
    +part('2. Địa điểm và hình thức','<div class="form-grid">'+field('location','Tỉnh / thành phố',j.location,'text','required')
      +select('work_mode','Hình thức',modes,j.work_mode)+select('employment_schedule','Lịch làm việc',schedules,d.employment_schedule)
      +wide(area('working_hours','Thời gian làm việc (mỗi dòng một khung giờ)',d.working_hours,'rows="2" maxlength="500" placeholder="Thứ 2 - Thứ 6 (từ 08:00 đến 17:00)"'))
      +wide(field('address','Địa chỉ cụ thể',d.address,'text','maxlength="255"'))+'</div>')
    +part('3. Yêu cầu ứng viên','<div class="form-grid">'+field('experience','Kinh nghiệm',d.experience,'text','maxlength="100" placeholder="Ví dụ: Không yêu cầu, 6 tháng"')
      +select('education','Học vấn',educations,d.education)+field('quantity','Số lượng tuyển',d.quantity,'number','min="1" max="1000"')
      +wide(field('skills','Tất cả kỹ năng, cách nhau bằng dấu phẩy',j.skills?.join(', ')))
      +wide(field('required_skills','Kỹ năng bắt buộc (chọn từ danh sách trên)',d.skill_priorities?.filter(s=>s.priority==='required').map(s=>s.name).join(', ')))+'</div>')
    +part('4. Phụ cấp và hạn nộp','<div class="form-grid">'+field('salary_min','Lương từ',j.salary_min,'number','min="0"')
      +field('salary_max','Lương đến',j.salary_max,'number','min="0"')+field('deadline','Hạn nộp',j.deadline,'date')+'</div>')
    +part('5. Nội dung tin','<div class="stack">'+area('description','Mô tả',j.description,'required minlength="15"')
      +area('requirements','Yêu cầu',j.requirements,'required minlength="4"')+area('benefits','Quyền lợi',d.benefits)+'</div>');
}
function jobPayload(data){
  return {...data,company_id:Number(data.company_id),skills:list(data.skills),required_skills:list(data.required_skills),deadline:data.deadline||null,
    quantity:data.quantity?Number(data.quantity):null,education:data.education||null,
    employment_schedule:data.employment_schedule||null,
    salary_min:data.salary_min?Number(data.salary_min):null,salary_max:data.salary_max?Number(data.salary_max):null};
}
const WEEKDAYS=['Chủ nhật','Thứ 2','Thứ 3','Thứ 4','Thứ 5','Thứ 6','Thứ 7'];
const OPEN_INTERVIEW=['invited','confirmed','reschedule_requested'];
const modeName=Object.fromEntries(modes);
const tabs=[['jobs','Tin tuyển dụng'],['interviews','Lịch phỏng vấn'],['profile','Hồ sơ công ty']];
let activeTab='jobs',menusBound=false;
const two=n=>String(n).padStart(2,'0');
const startOfDay=d=>new Date(d.getFullYear(),d.getMonth(),d.getDate());
const dateText=key=>key.slice(8,10)+'/'+key.slice(5,7)+'/'+key.slice(0,4);
const dayTitle=key=>WEEKDAYS[new Date(+key.slice(0,4),+key.slice(5,7)-1,+key.slice(8,10)).getDay()]+', '+dateText(key);

// Trạng thái hiển thị của tin: xanh (đang mở), vàng (chờ duyệt), đỏ (bị từ chối), xám (đã đóng hoặc hết hạn).
function jobState(j){
  if(j.status==='closed')return ['closed','Đã đóng'];
  if(j.moderation_status==='rejected')return ['rejected','Bị từ chối'];
  if(j.moderation_status==='pending')return ['pending','Chờ duyệt'];
  if(!j.active)return ['closed','Hết hạn'];
  return ['open','Đang mở'];
}
function deadlineCell(j){
  if(!j.deadline)return '<span class="job-sub">Không có hạn</span>';
  const [y,m,d]=j.deadline.split('-').map(Number);
  const days=Math.round((new Date(y,m-1,d)-startOfDay(new Date()))/864e5);
  const left=days>0?'Còn '+days+' ngày':days===0?'Hết hạn hôm nay':'Đã quá hạn';
  return '<div>'+two(d)+'/'+two(m)+'/'+y+'</div><div class="job-sub">'+left+'</div>';
}
const menuItem=(action,label,value)=>'<button type="button" data-action="'+action+'" data-value="'+esc(value)+'">'+label+'</button>';
function jobRow(j){
  const [state,label]=jobState(j),rejected=state==='rejected';
  const items=[];
  if(!rejected)items.push('<a href="#edit/'+j.id+'">Chỉnh tin</a>');
  if(j.status==='open')items.push(menuItem('close','Đóng tin',j.id));
  if(j.status==='closed')items.push(menuItem('reopen','Mở lại tin',j.id));
  items.push(menuItem('delete','Xóa tin',j.id));
  return '<tr><td><div class="job-title">'+esc(j.title)+'</div><div class="job-sub">'+esc(j.location)+' · '+esc(modeName[j.work_mode]||j.work_mode)+'</div>'
    +(rejected&&j.rejection_reason?'<p class="job-reason">Lý do từ chối: '+esc(j.rejection_reason)+'</p>':'')+'</td>'
    +'<td data-label="Trạng thái"><span class="state state-'+state+'">'+label+'</span></td>'
    +'<td data-label="Hạn nộp">'+deadlineCell(j)+'</td>'
    +'<td data-label="Đơn">'+(j.application_count??0)+(j.new_application_count?' <span class="badge">'+j.new_application_count+' mới</span>':'')+'</td>'
    +'<td><div class="row-actions">'+(rejected?'<a class="button" href="#edit/'+j.id+'">Sửa và gửi lại</a>':'<a class="button" href="#applicants/'+j.id+'">Hồ sơ ứng tuyển</a>')
    +'<details class="row-menu"><summary class="menu-btn" aria-label="Thao tác khác">…</summary><div class="menu-list">'+items.join('')+'</div></details></div></td></tr>';
}
const jobsPanel=jobs=>jobs.length?box('<table class="data-table"><thead><tr><th>Tin tuyển dụng</th><th>Trạng thái</th><th>Hạn nộp</th><th>Đơn</th><th>Thao tác</th></tr></thead><tbody>'
  +jobs.map(jobRow).join('')+'</tbody></table>'):empty('Chưa có tin tuyển dụng.');

function interviewCard(i,highlight){
  const at=String(i.scheduled_at);
  return '<article class="panel interview'+(highlight?' interview-alert':'')+'"><h3>'+esc(i.student_name)+'</h3>'
    +(i.job_title?'<p class="job-sub">'+esc(i.job_title)+'</p>':'')
    +tags((highlight?dateText(at.slice(0,10))+' ':'')+at.slice(11,16),status(i.status))
    +copy(i.location)+(i.response?copy(i.response):'')
    +(OPEN_INTERVIEW.includes(i.status)?btn('cancel','Hủy lịch',i.id):'')+'</article>';
}
function interviewsPanel(interviews){
  if(!interviews.length)return empty('Chưa có lịch phỏng vấn.');
  const asks=interviews.filter(i=>i.status==='reschedule_requested');
  const days=new Map();
  for(const i of interviews.filter(i=>i.status!=='reschedule_requested')){
    const key=String(i.scheduled_at).slice(0,10);
    days.set(key,[...(days.get(key)||[]),i]);
  }
  return (asks.length?'<h3 class="group-title">Sinh viên xin đổi lịch ('+asks.length+')</h3>'+asks.map(i=>interviewCard(i,true)).join(''):'')
    +[...days].sort(([a],[b])=>a<b?-1:1).map(([key,rows])=>'<h3 class="group-title">'+esc(dayTitle(key))+'</h3>'
      +[...rows].sort((a,b)=>a.scheduled_at<b.scheduled_at?-1:1).map(i=>interviewCard(i,false)).join('')).join('');
}
// Phỏng vấn còn hiệu lực từ bây giờ đến hết Chủ nhật của tuần này (giờ Việt Nam, cùng múi giờ với dữ liệu).
function interviewsThisWeek(interviews){
  const now=new Date(),today=startOfDay(now);
  const nextMonday=new Date(today.getFullYear(),today.getMonth(),today.getDate()+7-(now.getDay()+6)%7);
  return interviews.filter(i=>{
    const at=new Date(i.scheduled_at);
    return OPEN_INTERVIEW.includes(i.status)&&at>=now&&at<nextMonday;
  }).length;
}
const profilePanel=companies=>companies.map(c=>box('<h3>'+esc(c.name)+'</h3><div class="profile-cols"><div class="logo-edit">'+logoTile(c.id,c.name,true,c.has_logo)
  +form('logo-'+c.id,'<label class="field">Logo (PNG, JPG hoặc WebP, tối đa 2 MB)<input type="file" name="file" required accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"></label>','Tải logo lên')
  +(c.has_logo?btn('remove-logo','Xóa logo',c.id):'')+'</div>'
  +form('co-'+c.id,field('name','Tên',c.name)+field('industry','Ngành',c.industry)+field('city','Thành phố',c.city)
    +field('address','Địa chỉ văn phòng',c.details?.address,'text','maxlength="400"')
    +field('work_schedule','Lịch làm việc',c.details?.work_schedule,'text','maxlength="255"')
    +area('description','Mô tả',c.description)+area('benefits','Quyền lợi',c.details?.benefits),'Lưu hồ sơ')+'</div>')).join('');

function bindMenus(){
  if(menusBound)return;
  menusBound=true;
  const closeAll=()=>{for(const m of document.querySelectorAll('.row-menu[open]'))m.removeAttribute('open');};
  document.addEventListener('click',e=>{
    for(const m of document.querySelectorAll('.row-menu[open]'))if(!m.contains(e.target)||e.target.closest('.menu-list'))m.removeAttribute('open');
  });
  document.addEventListener('keydown',e=>{if(e.key==='Escape')closeAll();});
}
async function workspace({root,user,reload}){
  if(!user)return loginRequired(root);
  const [companies,jobs,interviews]=await Promise.all([api('/companies/mine'),api('/jobs/mine'),api('/interviews')]);
  if(!companies.length){
    root.innerHTML=heading('Quản lý tuyển dụng','Đăng tin, xử lý đơn ứng tuyển và đặt lịch.')+empty('Tài khoản chưa thuộc doanh nghiệp.');
    return;
  }
  const asks=interviews.filter(i=>i.status==='reschedule_requested').length;
  const stats=[['Tin đang mở',jobs.filter(j=>jobState(j)[0]==='open').length],['Chờ duyệt',jobs.filter(j=>jobState(j)[0]==='pending').length],
    ['Đơn chưa xử lý',jobs.filter(j=>j.status!=='closed').reduce((sum,j)=>sum+(j.new_application_count||0),0)],['Phỏng vấn tuần này',interviewsThisWeek(interviews)]];
  const panels={jobs:jobsPanel(jobs),interviews:interviewsPanel(interviews),profile:profilePanel(companies)};
  root.innerHTML='<div class="ws-head"><div class="ws-company">'+(companies.length===1?logoTile(companies[0].id,companies[0].name,true,companies[0].has_logo):'')
    +'<div><h1>'+esc(companies.map(c=>c.name).join(' · '))+'</h1><p class="muted">Quản lý tuyển dụng</p></div></div>'
    +'<div class="row">'+link('recruitment-stats','Thống kê tuyển dụng')
    +(companies.some(c=>c.can_manage_members)?link('company-members','Thành viên'):'')
    +'<button type="button" id="toggle-new-job" aria-expanded="false" aria-controls="new-job-panel">Đăng tin mới</button></div></div>'
    +'<section class="panel" id="new-job-panel" hidden>'+form('new-job',jobFields(companies),'Gửi kiểm duyệt')+'</section>'
    +'<div class="stat-grid">'+stats.map(([label,n])=>'<div class="stat"><strong>'+n+'</strong><span>'+esc(label)+'</span></div>').join('')+'</div>'
    +'<div class="co-tabs ws-tabs" role="group" aria-label="Mục quản lý">'+tabs.map(([key,text])=>'<button type="button" class="co-tab" data-tab="'+key+'" aria-current="'+(key===activeTab)+'">'+text
      +(key==='interviews'&&asks?'<span class="badge" aria-label="'+asks+' lời xin đổi lịch">'+asks+'</span>':'')+'</button>').join('')+'</div>'
    +tabs.map(([key])=>'<div data-panel="'+key+'"'+(key===activeTab?'':' hidden')+'>'+panels[key]+'</div>').join('');
  const toggle=root.querySelector('#toggle-new-job'),newJob=root.querySelector('#new-job-panel');
  toggle.addEventListener('click',()=>{newJob.hidden=!newJob.hidden;toggle.setAttribute('aria-expanded',String(!newJob.hidden));});
  for(const tab of root.querySelectorAll('[data-tab]'))tab.addEventListener('click',()=>{
    activeTab=tab.dataset.tab;
    for(const t of root.querySelectorAll('[data-tab]'))t.setAttribute('aria-current',String(t.dataset.tab===activeTab));
    for(const p of root.querySelectorAll('[data-panel]'))p.hidden=p.dataset.panel!==activeTab;
  });
  bindMenus();
  for(const c of companies){
    bindForm(root,'co-'+c.id,async data=>{await api('/companies/'+c.id,{method:'PUT',data});toast('Đã lưu');await reload();});
    bindForm(root,'logo-'+c.id,async data=>{await api('/companies/'+c.id+'/logo',{method:'POST',data});toast('Đã cập nhật logo');await reload();},{keepFiles:true});
  }
  action(root,'remove-logo',async id=>{if(confirm('Xóa logo doanh nghiệp?')){await api('/companies/'+id+'/logo',{method:'DELETE'});toast('Đã xóa logo');await reload();}});
  bindForm(root,'new-job',async data=>{await api('/jobs',{method:'POST',data:jobPayload(data)});activeTab='jobs';toast('Tin đã vào hàng chờ');await reload();});
  for(const [name,method] of [['close','POST'],['delete','DELETE']])action(root,name,async id=>{
    if(confirm(name==='close'?'Đóng tin này? Các ứng viên đang chờ sẽ được thông báo.':'Xóa tin này?')){await api('/jobs/'+id+(name==='close'?'/close':''),{method});await reload();}
  });
  action(root,'reopen',async id=>{
    const job=await api('/jobs/'+id+'/reopen',{method:'POST'});
    toast(job.moderation_status==='approved'?'Đã mở lại tin':'Đã mở lại tin. Tin đang chờ kiểm duyệt trước khi hiển thị công khai.');
    await reload();
  });
  action(root,'cancel',async id=>{if(confirm('Hủy lời mời này?')){await api('/interviews/'+id+'/cancel',{method:'POST'});await reload();}});
}
async function edit({root,user,args}){
  if(!user)return loginRequired(root);
  const id=Number(args[0]);
  const [c,j]=await Promise.all([api('/companies/mine'),api('/jobs/'+id)]);
  root.innerHTML=heading('Chỉnh sửa tin',j.title)
    +'<p class="muted">Với tin đã duyệt: sửa phần nội dung chữ (tiêu đề, mô tả, yêu cầu, quyền lợi, lương, ngành, địa điểm, địa chỉ, kỹ năng, kinh nghiệm, giờ làm) sẽ phải kiểm duyệt lại trước khi tin hiển thị. Hạn nộp, số lượng, học vấn, hình thức, cấp độ và loại hình làm việc có hiệu lực ngay.</p>'
    +box(form('edit',jobFields(c.filter(x=>x.id===j.company_id),j),'Lưu thay đổi'));
  bindForm(root,'edit',async data=>{
    const saved=await api('/jobs/'+id,{method:'PUT',data:jobPayload(data)});
    toast(saved.moderation_status==='pending'?'Đã lưu. Tin cần được kiểm duyệt trước khi hiển thị công khai.':'Đã lưu thay đổi.');
    location.hash='workspace';
  });
}
// ---- Dùng chung cho các trang đơn ứng tuyển, kiểm duyệt và quản trị ----
const statTile=([label,n])=>'<div class="stat"><strong>'+n+'</strong><span>'+esc(label)+'</span></div>';
const stateChip=(kind,text)=>'<span class="state state-'+kind+'">'+esc(text)+'</span>';
const chipRow=(label,items,kind='')=>items?.length?'<div class="chip-row"><span class="job-sub">'+esc(label)+'</span>'
  +items.map(s=>'<span class="tag'+(kind?' '+kind:'')+'">'+esc(s)+'</span>').join('')+'</div>':'';
const dateTime=iso=>{const s=String(iso);return dateText(s.slice(0,10))+' '+s.slice(11,16);};
const ago=iso=>{const days=Math.round((startOfDay(new Date())-startOfDay(new Date(iso)))/864e5);return days<=0?'hôm nay':days+' ngày trước';};
const levelName={intern:'Thực tập',fresher:'Fresher',junior:'Junior',senior:'Senior'};
const scheduleName={part_time:'Bán thời gian',full_time:'Toàn thời gian'};
const roleName={student:'Sinh viên',company_member:'Doanh nghiệp',staff:'Kiểm duyệt',admin:'Quản trị'};
const fileName=source=>String(source).replaceAll('\\','/').split('/').pop();
// Nút có data-toggle="<id>" mở/đóng khối có id đó; mở khối này thì đóng các khối .inline-form khác cùng thẻ.
function bindToggles(container){
  container.addEventListener('click',e=>{
    const button=e.target.closest('[data-toggle]');
    const panel=button&&container.querySelector('#'+button.dataset.toggle);
    if(!panel)return;
    for(const other of (button.closest('.panel')||container).querySelectorAll('.inline-form'))if(other!==panel)other.hidden=true;
    panel.hidden=!panel.hidden;
    if(!panel.hidden)panel.querySelector('textarea,input')?.focus();
  });
}

// ---- Hồ sơ ứng tuyển (doanh nghiệp) ----
const appView={job:null,filter:'all',sort:'match'};
const appKind={pending:'pending',reviewing:'info',accepted:'open',rejected:'rejected',withdrawn:'closed'};
const appFilters=[
  ['all','Tất cả',()=>true],
  ['pending','Chờ xử lý',a=>a.status==='pending'],
  ['reviewing','Đang xét',a=>a.status==='reviewing'],
  ['accepted','Đã nhận',a=>a.status==='accepted'],
  ['closed','Từ chối / Đã rút',a=>['rejected','withdrawn'].includes(a.status)]];
const appSorts={
  match:(a,b)=>(b.match_score??-1)-(a.match_score??-1)||a.id-b.id,
  new:(a,b)=>String(b.submitted_at).localeCompare(String(a.submitted_at))||b.id-a.id};
// Mỗi đơn lấy một lịch phỏng vấn: ưu tiên lịch còn hiệu lực, nếu không thì lịch gần nhất.
function latestInterviews(interviews){
  const map=new Map();
  for(const i of interviews){
    const old=map.get(i.application_id);
    if(!old||OPEN_INTERVIEW.includes(i.status)||!OPEN_INTERVIEW.includes(old.status))map.set(i.application_id,i);
  }
  return map;
}
function interviewLine(i){
  if(!i)return '';
  return '<div class="interview-line'+(i.status==='reschedule_requested'?' interview-alert':'')+'"><strong>Phỏng vấn:</strong> '+esc(dateTime(i.scheduled_at))
    +' · '+esc(i.location)+' · '+esc(status(i.status))+(i.response?'<div class="job-sub">'+esc(i.response)+'</div>':'')+'</div>';
}
function applicantCard(a,iv){
  const open=['pending','reviewing'].includes(a.status);
  const canInvite=!['rejected','withdrawn'].includes(a.status)&&!(iv&&['invited','confirmed'].includes(iv.status));
  const match=a.match_reason||{};
  const skills=a.skills||[];
  return '<article class="panel applicant"><div class="applicant-head"><span class="avatar" aria-hidden="true">'+esc(String(a.student_name||'?').trim().charAt(0).toUpperCase())+'</span>'
    +'<div class="applicant-name"><h3>'+esc(a.student_name)+'</h3><p class="job-sub">'
    +esc([a.major,'Nộp '+dateText(String(a.submitted_at).slice(0,10))+' ('+ago(a.submitted_at)+')'].filter(Boolean).join(' · '))+'</p></div>'
    +'<div class="applicant-side">'+stateChip(appKind[a.status]||'closed',status(a.status))+(a.match_score!=null?'<span class="score">Phù hợp '+esc(a.match_score)+'%</span>':'')+'</div></div>'
    +chipRow('Kỹ năng',skills.slice(0,10).concat(skills.length>10?['+'+(skills.length-10)]:[]))
    +chipRow('Khớp yêu cầu',match.matched_skills,'chip-ok')+chipRow('Còn thiếu',match.missing_skills,'chip-miss')
    +(a.status==='rejected'&&a.decision_reason?'<p class="job-reason">Lý do từ chối: '+esc(a.decision_reason)+'</p>':'')
    +(String(a.cover_letter||'').trim()?'<details class="letter"><summary>Thư xin việc</summary>'+copy(a.cover_letter)+'</details>':'')
    +tags(a.school,a.specialization,a.study_year?'Năm '+a.study_year:'')+(a.summary?copy(a.summary):'')
    +interviewLine(iv)
    +(a.completed_at?tags('Đã hoàn thành kỳ thực tập'):a.status==='accepted'?btn('complete-placement','Xác nhận hoàn thành kỳ thực tập',a.id):'')
    +(a.interviewer_rating||iv?.status==='confirmed'&&new Date(iv.scheduled_at+'+07:00')<=new Date()
      ?'<details><summary>Đánh giá sau phỏng vấn</summary>'+form('feedback-'+a.id,
        select('rating','Điểm ứng viên',Array.from({length:5},(_,i)=>[i+1,(i+1)+'/5']),String(a.interviewer_rating||5))
        +area('note','Nhận xét nội bộ',a.interviewer_note,'required maxlength="2000"'),'Lưu đánh giá')+'</details>':'')
    +'<div class="row applicant-actions">'+(a.cv_id?'<a class="button secondary" href="/api/applications/'+a.id+'/cv">Tải CV</a>':'')
    +(canInvite?'<button type="button" class="secondary" data-toggle="invite-panel-'+a.id+'">Mời phỏng vấn</button>':'')
    +(open?'<button type="button" data-action="accept" data-value="'+a.id+'">Nhận</button><button type="button" class="secondary danger" data-toggle="reject-panel-'+a.id+'">Từ chối</button>':'')+'</div>'
    +(canInvite?'<div class="inline-form" id="invite-panel-'+a.id+'" hidden>'+form('invite-'+a.id,field('scheduled_at','Giờ Việt Nam','','datetime-local','required')
      +field('location','Địa điểm / liên kết','','text','required')+area('note','Ghi chú'),'Gửi lời mời')+'</div>':'')
    +(open?'<div class="inline-form" id="reject-panel-'+a.id+'" hidden>'+form('reject-'+a.id,area('reason','Lý do từ chối (sinh viên sẽ nhận được lý do này)','','required maxlength="2000"'),'Xác nhận từ chối')+'</div>':'')
    +'</article>';
}
async function applicants({root,user,args,reload}){
  if(!user)return loginRequired(root);
  const id=Number(args[0]);
  const [rows,j,interviews]=await Promise.all([api('/applications/job/'+id),api('/jobs/'+id),api('/interviews')]);
  if(appView.job!==id)Object.assign(appView,{job:id,filter:'all',sort:'match'});
  const count=fn=>rows.filter(fn).length;
  const head='<div class="ws-head"><div><h1>Hồ sơ ứng tuyển</h1><p class="muted">'+esc(j.title)+' · '+esc(jobState(j)[1])+' · Hạn '
    +esc(j.deadline?dateText(j.deadline):'linh hoạt')+'</p></div><a class="button secondary" href="#workspace">Về quản lý</a></div>';
  if(!rows.length){root.innerHTML=head+empty('Chưa có đơn ứng tuyển.');return;}
  const ivs=latestInterviews(interviews);
  root.innerHTML=head
    +'<div class="stat-grid">'+[['Tổng số đơn',rows.length],['Chờ xử lý',count(a=>a.status==='pending')],['Đang xét',count(a=>a.status==='reviewing')],['Đã nhận',count(a=>a.status==='accepted')]].map(statTile).join('')+'</div>'
    +'<div class="co-tabs ws-tabs" role="group" aria-label="Lọc đơn theo trạng thái">'+appFilters.map(([key,text,fn])=>'<button type="button" class="co-tab" data-filter="'+key+'" aria-current="'
      +(key===appView.filter)+'">'+esc(text)+' ('+count(fn)+')</button>').join('')+'</div>'
    +'<div class="toolbar">'+select('sort','Sắp xếp',[['match','Phù hợp nhất'],['new','Mới nhất']],appView.sort)+field('applicant-query','Tìm theo tên, ngành hoặc kỹ năng','','search')+'</div><div id="applicant-list"></div>';
  const listEl=root.querySelector('#applicant-list');
  const query=root.querySelector('[name="applicant-query"]');
  function paint(){
    const fn=appFilters.find(f=>f[0]===appView.filter)[2];
    const term=query.value.trim().toLocaleLowerCase('vi');
    const shown=rows.filter(a=>fn(a)&&[a.student_name,a.major,...(a.skills||[])].join(' ').toLocaleLowerCase('vi').includes(term))
      .sort(appSorts[appView.sort]);
    listEl.innerHTML=shown.length?shown.map(a=>applicantCard(a,ivs.get(a.id))).join(''):empty('Không có đơn nào trong mục này.');
    action(listEl,'complete-placement',async id=>{
      if(!confirm('Xác nhận sinh viên đã hoàn thành kỳ thực tập?'))return;
      await api('/applications/'+id+'/internship-completed',{method:'POST'});await reload();
    });
    for(const a of shown){
      bindForm(listEl,'feedback-'+a.id,async data=>{
        await api('/applications/'+a.id+'/interview-feedback',{method:'PUT',data:{rating:Number(data.rating),note:data.note}});
        toast('Đã lưu đánh giá');await reload();
      });
      bindForm(listEl,'invite-'+a.id,async data=>{await api('/interviews',{method:'POST',data:{...data,application_id:a.id}});toast('Đã gửi lời mời');await reload();});
      bindForm(listEl,'reject-'+a.id,async data=>{
        if(!data.reason.trim())throw new Error('Nhập lý do từ chối.');
        await api('/applications/'+a.id+'/status',{method:'PATCH',data:{status:'rejected',reason:data.reason}});toast('Đã từ chối đơn');await reload();
      });
    }
    action(listEl,'accept',async value=>{
      if(confirm('Nhận đơn ứng tuyển này?')){await api('/applications/'+value+'/status',{method:'PATCH',data:{status:'accepted'}});toast('Đã nhận đơn');await reload();}
    });
  }
  query.addEventListener('input',paint);
  bindToggles(listEl);
  for(const tab of root.querySelectorAll('[data-filter]'))tab.addEventListener('click',()=>{
    appView.filter=tab.dataset.filter;
    for(const t of root.querySelectorAll('[data-filter]'))t.setAttribute('aria-current',String(t.dataset.filter===appView.filter));
    paint();
  });
  root.querySelector('[name="sort"]').addEventListener('change',e=>{appView.sort=e.target.value;paint();});
  paint();
}

// ---- Kiểm duyệt tin (staff, admin) ----
const mod={sel:null,flagsOnly:false};
function modDetail(j){
  const d=j.details||{};
  const facts=[['Địa điểm',j.location],['Hình thức',modeName[j.work_mode]||j.work_mode],['Cấp độ',levelName[j.level]||j.level],['Ngành',j.category],
    ['Lương',money(j.salary_min,j.salary_max)],['Hạn nộp',j.deadline?dateText(j.deadline):'Linh hoạt'],['Lịch làm việc',scheduleName[d.employment_schedule]],
    ['Thời gian làm việc',d.working_hours],['Địa chỉ',d.address],['Kinh nghiệm',d.experience],['Học vấn',d.education],['Số lượng tuyển',d.quantity]].filter(([,v])=>v);
  const last=j.last_review;
  return '<section class="panel mod-detail"><p class="job-sub">'+esc(j.company_name)+'</p><h2 class="mod-title">'+esc(j.title)+'</h2>'
    +(j.flags?.length?'<div class="alert"><strong>Cảnh báo hệ thống</strong><ul class="bullets">'+j.flags.map(f=>'<li>'+esc(f)+'</li>').join('')+'</ul></div>':'')
    +(last?'<p class="'+(last.decision==='rejected'?'job-reason':'job-sub')+'">Lần duyệt trước: '
      +(last.decision==='rejected'?'Từ chối'+(last.reason?' — '+esc(last.reason):''):'Đã duyệt')+'</p>':'')
    +'<dl class="facts fact-grid">'+facts.map(([k,v])=>'<div><dt>'+esc(k)+'</dt><dd>'+esc(v)+'</dd></div>').join('')+'</dl>'
    +'<h3 class="co-sub">Mô tả</h3>'+copy(j.description)+'<h3 class="co-sub">Yêu cầu</h3>'+copy(j.requirements)
    +(d.benefits?'<h3 class="co-sub">Quyền lợi</h3>'+copy(d.benefits):'')
    +(j.skills?.length?'<h3 class="co-sub">Kỹ năng</h3>'+tags(...j.skills):'')
    +'<div class="row mod-actions"><button type="button" data-action="approve" data-value="'+j.id+'">Duyệt</button>'
    +'<button type="button" class="secondary danger" data-toggle="mod-reject">Từ chối</button></div>'
    +'<div class="inline-form" id="mod-reject" hidden>'+form('review-'+j.id,area('reason','Lý do từ chối (doanh nghiệp sẽ nhận được lý do này)','','required maxlength="2000"'),'Xác nhận từ chối')+'</div></section>';
}
async function moderation({root,user,reload}){
  if(!user)return loginRequired(root);
  const rows=await api('/jobs/moderation');
  root.innerHTML=heading('Hàng chờ kiểm duyệt')
    +'<div class="stat-grid stat-grid-3">'+[['Chờ duyệt',rows.length],['Có cảnh báo',rows.filter(j=>j.flags?.length).length],['Gửi lại',rows.filter(j=>j.last_review).length]].map(statTile).join('')+'</div>'
    +(rows.length?'<div class="toolbar"><label class="check"><input type="checkbox" id="only-flags"'+(mod.flagsOnly?' checked':'')+'> Chỉ tin có cảnh báo</label></div>'
      +'<div class="mod-layout"><div class="mod-list" id="mod-list"></div><div id="mod-detail"></div></div>':empty('Hàng chờ đã trống.'));
  if(!rows.length)return;
  const listEl=root.querySelector('#mod-list'),detailEl=root.querySelector('#mod-detail');
  function paint(){
    const shown=rows.filter(j=>!mod.flagsOnly||j.flags?.length);
    if(!shown.some(j=>j.id===mod.sel))mod.sel=shown[0]?.id??null;
    listEl.innerHTML=shown.length?shown.map(j=>'<button type="button" class="mod-item" data-job="'+j.id+'" aria-current="'+(j.id===mod.sel)+'"><strong>'+esc(j.title)+'</strong>'
      +'<span class="job-sub">'+esc(j.company_name)+'</span><span class="mod-tags">'+(j.flags?.length?stateChip('pending',j.flags.length+' cảnh báo'):'')
      +(j.last_review?stateChip('info','Gửi lại'):'')+'</span></button>').join(''):empty('Không có tin nào có cảnh báo.');
    const job=shown.find(j=>j.id===mod.sel);
    detailEl.innerHTML=job?modDetail(job):'';
    if(!job)return;
    bindForm(detailEl,'review-'+job.id,async data=>{
      if(!data.reason.trim())throw new Error('Nhập lý do từ chối để doanh nghiệp biết cần sửa gì.');
      await api('/jobs/'+job.id+'/review',{method:'POST',data:{decision:'rejected',reason:data.reason}});toast('Đã từ chối tin');await reload();
    });
    action(detailEl,'approve',async value=>{await api('/jobs/'+value+'/review',{method:'POST',data:{decision:'approved',reason:''}});toast('Đã duyệt tin');await reload();});
  }
  listEl.addEventListener('click',e=>{
    const item=e.target.closest('[data-job]');
    if(item){mod.sel=Number(item.dataset.job);paint();}
  });
  bindToggles(detailEl);
  root.querySelector('#only-flags').addEventListener('change',e=>{mod.flagsOnly=e.target.checked;paint();});
  paint();
}

// ---- Quản lý tài khoản (admin) ----
const acct={q:'',role:'all',state:'all'};
async function accounts({root,user,reload}){
  if(!user)return loginRequired(root);
  const users=await api('/auth/users');
  const roles=[...new Set(users.map(u=>u.role))];
  const count=fn=>users.filter(fn).length;
  root.innerHTML=heading('Quản lý tài khoản')
    +'<div class="stat-grid">'+[['Tổng tài khoản',users.length],['Chưa kích hoạt',count(u=>!u.active)],['Bị khóa',count(u=>u.locked)],['Sinh viên',count(u=>u.role==='student')]].map(statTile).join('')+'</div>'
    +'<div class="toolbar toolbar-wide">'+field('q','Tìm theo email',acct.q,'search','placeholder="Nhập một phần email"')
    +select('role','Vai trò',[['all','Tất cả vai trò'],...roles.map(r=>[r,roleName[r]||r])],acct.role)
    +select('state','Trạng thái',[['all','Tất cả'],['active','Đang hoạt động'],['inactive','Chưa kích hoạt'],['locked','Bị khóa']],acct.state)+'</div><div id="acct-table"></div>';
  const tableEl=root.querySelector('#acct-table');
  function paint(){
    const q=acct.q.trim().toLowerCase();
    const shown=users.filter(u=>(!q||u.email.toLowerCase().includes(q))&&(acct.role==='all'||u.role===acct.role)
      &&(acct.state==='all'||(acct.state==='locked'?u.locked:acct.state==='inactive'?!u.active:u.active&&!u.locked)));
    const rowsShown=shown.slice(0,100);
    tableEl.innerHTML=shown.length?'<section class="panel"><table class="data-table"><thead><tr><th>Email</th><th>Vai trò</th><th>Trạng thái</th><th>Thao tác</th></tr></thead><tbody>'
      +rowsShown.map(u=>'<tr><td><div class="job-title">'+esc(u.email)+'</div></td><td data-label="Vai trò">'+esc(roleName[u.role]||u.role)+'</td>'
        +'<td data-label="Trạng thái">'+(u.locked?stateChip('rejected','Bị khóa'):stateChip(u.active?'open':'pending',u.active?'Đang hoạt động':'Chưa kích hoạt'))+'</td>'
        +'<td><div class="row-actions">'+(!u.active?'<button type="button" class="secondary" data-toggle="activate-panel-'+u.id+'">Kích hoạt</button>'
          :u.locked?'<button type="button" class="secondary" data-action="unlock" data-value="'+u.id+'">Mở khóa</button>'
          :u.id!==user.id?'<button type="button" class="secondary danger" data-action="lock" data-value="'+u.id+'">Khóa</button>':'')+'</div></td></tr>'
        +(u.active?'':'<tr class="act-row inline-form" id="activate-panel-'+u.id+'" hidden><td colspan="4">'
          +form('activate-'+u.id,field('password','Mật khẩu ban đầu','','password','required minlength="10"'),'Xác nhận kích hoạt')+'</td></tr>')).join('')
      +'</tbody></table>'+(shown.length>rowsShown.length?'<p class="job-sub">Hiển thị '+rowsShown.length+' / '+shown.length+' tài khoản. Hãy tìm hoặc lọc để thu hẹp.</p>':'')+'</section>'
      :empty('Không có tài khoản phù hợp.');
    for(const u of rowsShown)bindForm(tableEl,'activate-'+u.id,async data=>{await api('/auth/users/'+u.id+'/activate',{method:'POST',data});toast('Đã kích hoạt tài khoản');await reload();});
    action(tableEl,'lock',async id=>{
      if(confirm('Khóa tài khoản này? Người dùng sẽ bị đăng xuất ngay và không đăng nhập lại được.')){await api('/auth/users/'+id+'/lock',{method:'POST'});toast('Đã khóa tài khoản');await reload();}
    });
    action(tableEl,'unlock',async id=>{await api('/auth/users/'+id+'/unlock',{method:'POST'});toast('Đã mở khóa tài khoản');await reload();});
  }
  bindToggles(tableEl);
  root.querySelector('[name="q"]').addEventListener('input',e=>{acct.q=e.target.value;paint();});
  root.querySelector('[name="role"]').addEventListener('change',e=>{acct.role=e.target.value;paint();});
  root.querySelector('[name="state"]').addEventListener('change',e=>{acct.state=e.target.value;paint();});
  paint();
}

// ---- Tài liệu chatbot (staff, admin) ----
const kb={q:'',status:'published'};
const docState=d=>d.status==='archived'?['closed','Đã lưu trữ']:d.vector_synced_at?['open','Đã lập chỉ mục']:['pending','Chờ lập chỉ mục'];
async function knowledge({root,user,reload}){
  if(!user)return loginRequired(root);
  const docs=await api('/knowledge');
  root.innerHTML='<div class="ws-head"><div>'+heading('Tài liệu chatbot')+'</div><button type="button" id="toggle-doc" aria-expanded="false" aria-controls="doc-panel">Thêm tài liệu</button></div>'
    +'<section class="panel" id="doc-panel" hidden><div class="co-tabs" role="group" aria-label="Cách thêm tài liệu"><button type="button" class="co-tab" data-doc-mode="add" aria-current="true">Nhập nội dung</button>'
    +'<button type="button" class="co-tab" data-doc-mode="upload" aria-current="false">Tải tệp</button></div>'
    +'<div class="inline-form" data-doc-form="add">'+form('add-doc',field('title','Tiêu đề','','text','required')+field('topic','Chủ đề','FAQ')
      +area('content','Nội dung','','required minlength="15"'),'Thêm tài liệu')+'</div>'
    +'<div class="inline-form" data-doc-form="upload" hidden>'+form('upload-doc',field('title','Tiêu đề','','text','required')
      +'<label class="field">Tệp văn bản (tối đa 50 MB, PDF tối đa 600 trang)<input name="file" type="file" required accept=".md,.txt,.pdf,.docx"></label>','Tải tài liệu')+'</div></section>'
    +'<div class="toolbar toolbar-wide">'+field('q','Tìm tài liệu',kb.q,'search','placeholder="Tiêu đề hoặc chủ đề"')
    +select('status','Trạng thái',[['published','Đang công khai'],['archived','Đã lưu trữ'],['all','Tất cả']],kb.status)+'</div><div id="kb-table"></div>';
  const tableEl=root.querySelector('#kb-table'),panel=root.querySelector('#doc-panel'),toggle=root.querySelector('#toggle-doc');
  function paint(){
    const q=kb.q.trim().toLowerCase();
    const shown=docs.filter(d=>(kb.status==='all'||d.status===kb.status)&&(!q||(d.title+' '+d.topic).toLowerCase().includes(q))).sort((a,b)=>b.id-a.id);
    tableEl.innerHTML=shown.length?'<section class="panel"><table class="data-table"><thead><tr><th>Tài liệu</th><th>Nguồn</th><th>Trạng thái</th><th>Thao tác</th></tr></thead><tbody>'
      +shown.map(d=>{
        const [kind,label]=docState(d),published=d.status==='published';
        const pdf=d.source.replaceAll('\\','/').startsWith('data/knowledge/')&&d.source.toLowerCase().endsWith('.pdf');
        return '<tr><td><div class="job-title">'+esc(d.title)+'</div><div class="job-sub">'+esc(d.topic)+' · v'+esc(d.version)+'</div></td>'
          +'<td data-label="Nguồn">'+esc(fileName(d.source))+'</td><td data-label="Trạng thái">'+stateChip(kind,label)+'</td>'
          +'<td><div class="row-actions">'+(published&&pdf?btn('reprocess','Đọc lại PDF',d.id):'')+(published?btn('archive','Lưu trữ',d.id):'')+'</div></td></tr>';
      }).join('')+'</tbody></table></section>':empty('Không có tài liệu phù hợp.');
    action(tableEl,'reprocess',async id=>{toast('Đang đọc lại PDF. Bản scan có thể mất vài phút.');await api('/knowledge/'+id+'/reprocess',{method:'POST'});toast('Đã đọc lại PDF');await reload();});
    action(tableEl,'archive',async id=>{if(confirm('Gỡ tài liệu khỏi tri thức công khai?')){await api('/knowledge/'+id,{method:'DELETE'});await reload();}});
  }
  toggle.addEventListener('click',()=>{panel.hidden=!panel.hidden;toggle.setAttribute('aria-expanded',String(!panel.hidden));});
  for(const tab of root.querySelectorAll('[data-doc-mode]'))tab.addEventListener('click',()=>{
    for(const t of root.querySelectorAll('[data-doc-mode]'))t.setAttribute('aria-current',String(t===tab));
    for(const f of root.querySelectorAll('[data-doc-form]'))f.hidden=f.dataset.docForm!==tab.dataset.docMode;
  });
  root.querySelector('[name="q"]').addEventListener('input',e=>{kb.q=e.target.value;paint();});
  root.querySelector('[name="status"]').addEventListener('change',e=>{kb.status=e.target.value;paint();});
  bindForm(root,'add-doc',async data=>{await api('/knowledge',{method:'POST',data});await reload();});
  bindForm(root,'upload-doc',async data=>{await api('/knowledge/upload',{method:'POST',data});await reload();},{keepFiles:true});
  paint();
}
export const pages={workspace,edit,applicants,moderation,accounts,knowledge};
