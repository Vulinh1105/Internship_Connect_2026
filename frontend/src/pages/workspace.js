import {api} from '../api/client.js';
import {esc,tags,box,copy,empty,heading,field,area,select,link,btn,form,grid,modes,list,status,toast,bindForm,action} from '../components/ui.js';
import {jobCard,loginRequired} from './public.js';
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
      +wide(field('skills','Kỹ năng, cách nhau bằng dấu phẩy',j.skills?.join(', ')))+'</div>')
    +part('4. Phụ cấp và hạn nộp','<div class="form-grid">'+field('salary_min','Lương từ',j.salary_min,'number','min="0"')
      +field('salary_max','Lương đến',j.salary_max,'number','min="0"')+field('deadline','Hạn nộp',j.deadline,'date')+'</div>')
    +part('5. Nội dung tin','<div class="stack">'+area('description','Mô tả',j.description,'required minlength="15"')
      +area('requirements','Yêu cầu',j.requirements,'required minlength="4"')+area('benefits','Quyền lợi',d.benefits)+'</div>');
}
function jobPayload(data){
  return {...data,company_id:Number(data.company_id),skills:list(data.skills),deadline:data.deadline||null,
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
  items.push(menuItem('delete','Xóa tin',j.id));
  return '<tr><td><div class="job-title">'+esc(j.title)+'</div><div class="job-sub">'+esc(j.location)+' · '+esc(modeName[j.work_mode]||j.work_mode)+'</div>'
    +(rejected&&j.rejection_reason?'<p class="job-reason">Lý do từ chối: '+esc(j.rejection_reason)+'</p>':'')+'</td>'
    +'<td data-label="Trạng thái"><span class="state state-'+state+'">'+label+'</span></td>'
    +'<td data-label="Hạn nộp">'+deadlineCell(j)+'</td>'
    +'<td data-label="Đơn">'+(j.application_count??0)+(j.new_application_count?' <span class="badge">'+j.new_application_count+' mới</span>':'')+'</td>'
    +'<td><div class="row-actions">'+(rejected?'<a class="button" href="#edit/'+j.id+'">Sửa và gửi lại</a>':'<a class="button" href="#applicants/'+j.id+'">Hồ sơ ứng tuyển</a>')
    +'<details class="row-menu"><summary class="menu-btn" aria-label="Thao tác khác">…</summary><div class="menu-list">'+items.join('')+'</div></details></div></td></tr>';
}
const jobsPanel=jobs=>jobs.length?box('<table class="job-table"><thead><tr><th>Tin tuyển dụng</th><th>Trạng thái</th><th>Hạn nộp</th><th>Đơn</th><th>Thao tác</th></tr></thead><tbody>'
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
    ['Đơn chưa xử lý',jobs.reduce((sum,j)=>sum+(j.new_application_count||0),0)],['Phỏng vấn tuần này',interviewsThisWeek(interviews)]];
  const panels={jobs:jobsPanel(jobs),interviews:interviewsPanel(interviews),profile:profilePanel(companies)};
  root.innerHTML='<div class="ws-head"><div class="ws-company">'+(companies.length===1?logoTile(companies[0].id,companies[0].name,true,companies[0].has_logo):'')
    +'<div><h1>'+esc(companies.map(c=>c.name).join(' · '))+'</h1><p class="muted">Quản lý tuyển dụng</p></div></div>'
    +'<button type="button" id="toggle-new-job" aria-expanded="false" aria-controls="new-job-panel">Đăng tin mới</button></div>'
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
    if(confirm('Cập nhật trạng thái tin này?')){await api('/jobs/'+id+(name==='close'?'/close':''),{method});await reload();}
  });
  action(root,'cancel',async id=>{if(confirm('Hủy lời mời này?')){await api('/interviews/'+id+'/cancel',{method:'POST'});await reload();}});
}
async function edit({root,user,args}){
  if(!user)return loginRequired(root);
  const id=Number(args[0]);
  const [c,j]=await Promise.all([api('/companies/mine'),api('/jobs/'+id)]);
  root.innerHTML=heading('Chỉnh sửa tin',j.title)+box(form('edit',jobFields(c.filter(x=>x.id===j.company_id),j),'Lưu và gửi duyệt lại'));
  bindForm(root,'edit',async data=>{await api('/jobs/'+id,{method:'PUT',data:jobPayload(data)});location.hash='workspace';});
}
async function applicants({root,user,args,reload}){
  if(!user)return loginRequired(root);
  const id=Number(args[0]);
  const [rows,j]=await Promise.all([api('/applications/job/'+id),api('/jobs/'+id)]);
  root.innerHTML=heading('Hồ sơ ứng tuyển',j.title)+link('workspace','Về quản lý')
    +(rows.length?rows.map(a=>box('<h3>'+esc(a.student_name)+'</h3>'+tags('#'+a.id,status(a.status),a.match_score!=null?'Phù hợp '+a.match_score+'%':'')
      +(a.match_reason?.reason?copy(a.match_reason.reason):'')+copy(a.cover_letter)+(a.cv_id?'<a href="/api/applications/'+a.id+'/cv">Tải CV đã nộp</a>':'')
      +(['pending','reviewing'].includes(a.status)?form('decision-'+a.id,select('status','Trạng thái',[['reviewing','Đang xét'],['accepted','Nhận'],['rejected','Từ chối']]),'Cập nhật'):'')
      +(!['rejected','withdrawn'].includes(a.status)?'<details><summary>Mời phỏng vấn</summary>'+form('invite-'+a.id,
        field('scheduled_at','Giờ Việt Nam','','datetime-local','required')+field('location','Địa điểm / liên kết','','text','required')
        +area('note','Ghi chú'),'Gửi lời mời')+'</details>':''))).join(''):empty());
  for(const a of rows){
    bindForm(root,'decision-'+a.id,async data=>{await api('/applications/'+a.id+'/status',{method:'PATCH',data});await reload();});
    bindForm(root,'invite-'+a.id,async data=>{await api('/interviews',{method:'POST',data:{...data,application_id:a.id}});toast('Đã gửi lời mời');await reload();});
  }
}
async function moderation({root,user,reload}){
  if(!user)return loginRequired(root);
  const rows=await api('/jobs/moderation');
  root.innerHTML=heading('Hàng chờ kiểm duyệt')+(rows.length?rows.map(j=>box('<div class="review-item"><div>'+jobCard(j)
    +(j.flags?.length?'<p class="alert">'+esc(j.flags.join(' · '))+'</p>':'')+'</div>'
    +form('review-'+j.id,select('decision','Quyết định',[['approved','Duyệt'],['rejected','Từ chối']])+area('reason','Lý do'),'Lưu quyết định')+'</div>')).join(''):empty('Hàng chờ đã trống.'));
  for(const j of rows)bindForm(root,'review-'+j.id,async data=>{
    if(data.decision==='rejected'&&!data.reason.trim())throw new Error('Nhập lý do từ chối để doanh nghiệp biết cần sửa gì.');
    await api('/jobs/'+j.id+'/review',{method:'POST',data});await reload();
  });
}
async function accounts({root,user,reload}){
  if(!user)return loginRequired(root);
  const users=await api('/auth/users');
  root.innerHTML=heading('Quản lý tài khoản')+grid(users.map(u=>'<article class="card"><h3>'+esc(u.email)+'</h3>'+tags(u.role,u.active?'Đang hoạt động':'Chưa kích hoạt')
    +(u.active?'':form('activate-'+u.id,field('password','Mật khẩu ban đầu','','password','required minlength="10"'),'Kích hoạt'))+'</article>'));
  for(const u of users)bindForm(root,'activate-'+u.id,async data=>{await api('/auth/users/'+u.id+'/activate',{method:'POST',data});await reload();});
}
async function knowledge({root,user,reload}){
  if(!user)return loginRequired(root);
  const docs=await api('/knowledge');
  root.innerHTML=heading('Tài liệu chatbot')+box(form('add-doc',field('title','Tiêu đề','','text','required')+field('topic','Chủ đề','FAQ')
    +area('content','Nội dung','','required minlength="15"'),'Thêm tài liệu'))
    +box(form('upload-doc',field('title','Tiêu đề','','text','required')+'<label class="field">Tệp văn bản (tối đa 50 MB, PDF tối đa 600 trang)<input name="file" type="file" required accept=".md,.txt,.pdf,.docx"></label>','Tải tài liệu'))
    +grid(docs.map(d=>'<article class="card"><h3>'+esc(d.title)+'</h3>'+tags(status(d.status),d.source,'v'+d.version,d.status==='published'?(d.vector_synced_at?'Đã lập chỉ mục':'Chờ lập chỉ mục'):'')
       +(d.status==='published'?btn('archive','Lưu trữ',d.id)
          +(d.source.replaceAll('\\','/').startsWith('data/knowledge/')&&d.source.toLowerCase().endsWith('.pdf')?btn('reprocess','Đọc lại PDF',d.id):''):'')+'</article>'));
  bindForm(root,'add-doc',async data=>{await api('/knowledge',{method:'POST',data});await reload();});
  bindForm(root,'upload-doc',async data=>{await api('/knowledge/upload',{method:'POST',data});await reload();},{keepFiles:true});
  action(root,'reprocess',async id=>{toast('Đang đọc lại PDF. Bản scan có thể mất vài phút.');await api('/knowledge/'+id+'/reprocess',{method:'POST'});toast('Đã đọc lại PDF');await reload();});
  action(root,'archive',async id=>{if(confirm('Gỡ tài liệu khỏi tri thức công khai?')){await api('/knowledge/'+id,{method:'DELETE'});await reload();}});
}
export const pages={workspace,edit,applicants,moderation,accounts,knowledge};
