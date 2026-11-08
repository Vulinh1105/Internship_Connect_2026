import {api} from '../api/client.js';
import {esc,tags,box,copy,empty,heading,field,area,select,link,btn,form,grid,modes,list,status,toast,bindForm,action} from '../components/ui.js';
import {jobCard,loginRequired} from './public.js';
import {logoTile} from '../components/media.js';

function jobFields(companies,j={}){
  return '<div class="form-grid">'+select('company_id','Doanh nghiệp',companies.map(c=>[c.id,c.name]),j.company_id)
    +field('title','Tiêu đề',j.title,'text','required')+field('category','Ngành',j.category,'text','required')
    +field('location','Địa điểm',j.location,'text','required')+select('work_mode','Hình thức',modes,j.work_mode)
    +select('level','Cấp độ',[['intern','Thực tập'],['fresher','Fresher'],['junior','Junior'],['senior','Senior']],j.level)
    +field('salary_min','Lương từ',j.salary_min,'number','min="0"')+field('salary_max','Lương đến',j.salary_max,'number','min="0"')
    +field('deadline','Hạn nộp',j.deadline,'date')+'</div>'+field('skills','Kỹ năng, cách nhau bằng dấu phẩy',j.skills?.join(', '))
    +area('description','Mô tả',j.description,'required minlength="15"')+area('requirements','Yêu cầu',j.requirements,'required minlength="4"')
    +area('benefits','Quyền lợi',j.details?.benefits);
}
function jobPayload(data){
  return {...data,company_id:Number(data.company_id),skills:list(data.skills),deadline:data.deadline||null,
    salary_min:data.salary_min?Number(data.salary_min):null,salary_max:data.salary_max?Number(data.salary_max):null};
}
async function workspace({root,user,reload}){
  if(!user)return loginRequired(root);
  const [companies,jobs,interviews]=await Promise.all([api('/companies/mine'),api('/jobs/mine'),api('/interviews')]);
  root.innerHTML=heading('Quản lý tuyển dụng','Đăng tin, xử lý đơn ứng tuyển và đặt lịch.')
    +'<div class="split"><div class="split-main">'+companies.map(c=>box('<details><summary>Chỉnh hồ sơ · '+esc(c.name)+'</summary>'
      +'<div class="logo-edit">'+logoTile(c.id,c.name,true,c.has_logo)
      +form('logo-'+c.id,'<label class="field">Logo (PNG, JPG hoặc WebP, tối đa 2 MB)<input type="file" name="file" required accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"></label>','Tải logo lên')
      +(c.has_logo?btn('remove-logo','Xóa logo',c.id):'')+'</div>'
      +form('co-'+c.id,
      field('name','Tên',c.name)+field('industry','Ngành',c.industry)+field('city','Thành phố',c.city)
      +area('description','Mô tả',c.description)+area('benefits','Quyền lợi',c.details?.benefits),'Lưu hồ sơ')+'</details>')).join('')
    +(companies.length?box('<details><summary>Đăng tin mới</summary>'+form('new-job',jobFields(companies),'Gửi kiểm duyệt')+'</details>'):empty('Tài khoản chưa thuộc doanh nghiệp.'))
    +'<h2>Tin đã đăng</h2>'+grid(jobs.map(j=>'<article class="card"><h3>'+esc(j.title)+'</h3>'+tags(status(j.status),status(j.moderation_status),j.deadline)
      +'<div class="row">'+link('applicants/'+j.id,'Hồ sơ ứng tuyển')+link('edit/'+j.id,'Chỉnh tin')
      +(j.status==='open'?btn('close','Đóng tin',j.id):'')+btn('delete','Xóa tin',j.id)+'</div></article>'))
    +'</div><aside class="split-side"><h2>Lịch phỏng vấn đã mời</h2>'+grid(interviews.map(i=>box('<h3>'+esc(i.student_name)+'</h3>'
      +tags(i.scheduled_at.replace('T',' '),status(i.status))+copy(i.location)+copy(i.response||'')
      +(['invited','confirmed','reschedule_requested'].includes(i.status)?btn('cancel','Hủy lịch',i.id):''))))+'</aside></div>';
  for(const c of companies){
    bindForm(root,'co-'+c.id,async data=>{await api('/companies/'+c.id,{method:'PUT',data});toast('Đã lưu');await reload();});
    bindForm(root,'logo-'+c.id,async data=>{await api('/companies/'+c.id+'/logo',{method:'POST',data});toast('Đã cập nhật logo');await reload();},{keepFiles:true});
  }
  action(root,'remove-logo',async id=>{if(confirm('Xóa logo doanh nghiệp?')){await api('/companies/'+id+'/logo',{method:'DELETE'});toast('Đã xóa logo');await reload();}});
  bindForm(root,'new-job',async data=>{await api('/jobs',{method:'POST',data:jobPayload(data)});toast('Tin đã vào hàng chờ');await reload();});
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
  for(const j of rows)bindForm(root,'review-'+j.id,async data=>{await api('/jobs/'+j.id+'/review',{method:'POST',data});await reload();});
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
