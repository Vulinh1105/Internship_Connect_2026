import {api} from '../api/client.js';
import {esc,tags,box,copy,empty,heading,field,select,link,btn,form,grid,money,modes,status,toast,bindForm,action} from '../components/ui.js';
import {jobCard,loginRequired} from './public.js';

const cvFile='<label class="field">Tệp .pdf, .docx hoặc .txt (tối đa 5 MB)<input type="file" name="file" required accept=".pdf,application/pdf,.docx,.txt"></label>';

async function profile({root,user,reload}){
  if(!user)return loginRequired(root);
  const cvs=await api('/students/me/cvs');
  root.innerHTML=heading('Hồ sơ & CV','Tải lên và quản lý CV dùng khi ứng tuyển.')
    +box('<h2>Tải CV</h2>'+form('upload',cvFile,'Tải lên'))
    +cvs.map(c=>box('<h3>'+esc(c.original_name)+'</h3>'
      +tags(c.confirmed?'Sẵn sàng sử dụng':'Chờ xác nhận')
      +(c.has_text===false?copy('Có thể đính kèm CV khi ứng tuyển. Gợi ý theo nội dung cần CV có văn bản đọc được.'):'')
      +'<div class="row"><a href="/api/students/me/cvs/'+c.id+'/download">Tải bản gốc</a>'
      +(!c.confirmed?btn('activate-cv','Dùng CV này',c.id):'')+btn('remove-cv','Xóa CV',c.id)+'</div>'
      +'<details><summary>Thay CV</summary>'+form('replace-'+c.id,cvFile,'Lưu CV mới')+'</details>')).join('');
  bindForm(root,'upload',async data=>{
    await api('/students/me/cvs',{method:'POST',data});toast('Đã tải CV');await reload();
  },{keepFiles:true});
  for(const c of cvs)bindForm(root,'replace-'+c.id,async data=>{
    await api('/students/me/cvs/'+c.id,{method:'PUT',data});toast('Đã thay CV');await reload();
  },{keepFiles:true});
  action(root,'activate-cv',async id=>{
    const cv=cvs.find(c=>c.id===Number(id));
    await api('/students/me/cvs/'+id+'/confirm',{method:'POST',data:cv.extracted});
    toast('CV đã sẵn sàng sử dụng');await reload();
  });
  action(root,'remove-cv',async id=>{
    if(confirm('Xóa CV khỏi hồ sơ? Các đơn đã nộp vẫn giữ bản CV đính kèm.')){
      await api('/students/me/cvs/'+id,{method:'DELETE'});toast('Đã xóa CV khỏi hồ sơ');await reload();
    }
  });
}
const matchRow=j=>{
  const pct=Math.max(0,Math.min(100,Math.round(Number(j.match_score)||0)));
  const workMode=modes.find(([key])=>key===j.work_mode)?.[1];
  return '<article class="card match-row"><div class="ring" style="--pct:'+pct+'" role="img" aria-label="'+(j.match_score!=null?'Phù hợp '+pct+'%':'Chưa có điểm')+'"><span>'+(j.match_score!=null?pct+'%':'–')+'</span></div>'
    +'<div class="match-body"><h3><a href="#job/'+j.id+'">'+esc(j.title)+'</a></h3><p class="muted">'+esc(j.company_name)+'</p>'
    +tags(j.location,workMode,j.category)
    +'<p class="job-summary">'+esc(money(j.salary_min,j.salary_max))+' · Hạn '+esc(j.deadline||'linh hoạt')+'</p>'
    +(j.reason?'<p>'+esc(j.reason)+'</p>':'')+(j.skills?.length?tags(...j.skills.slice(0,5)):'')+'</div>'
    +'<a class="card-link" href="#job/'+j.id+'">Xem thêm <span aria-hidden="true">→</span></a></article>';
};
async function matching({root,user}){
  if(!user)return loginRequired(root);
  const jobs=await api('/matching');
  root.innerHTML=heading('AI Matching','Gợi ý dựa trên hồ sơ, kỹ năng và nguyện vọng. Điểm số dùng để tham khảo khi chọn tin.')
    +(jobs.length?'<div class="match-list">'+jobs.map(matchRow).join('')+'</div>':empty())+(!jobs.length?link('profile','Cập nhật hồ sơ'):'');
}
async function saved({root,user,reload}){
  if(!user)return loginRequired(root);
  const jobs=await api('/jobs/saved');
  root.innerHTML=heading('Tin đã lưu')+grid(jobs.map(j=>'<div>'+jobCard(j)+'<div class="row">'+btn('remove','Bỏ lưu',j.id)+'</div></div>'));
  action(root,'remove',async id=>{await api('/jobs/'+id+'/saved?value=false',{method:'PUT'});await reload();});
}
async function applications({root,user,reload}){
  if(!user)return loginRequired(root);
  const [apps,interviews]=await Promise.all([api('/applications/me'),api('/interviews')]);
  root.innerHTML=heading('Đơn ứng tuyển','Theo dõi trạng thái và phản hồi lời mời phỏng vấn trên web.')
    +'<div class="split"><div class="split-main"><h2>Đơn của bạn</h2>'+(apps.length?apps.map(a=>box('<h3>'+esc(a.job_title)+'</h3>'+tags('#'+a.id,status(a.status),a.match_score!=null?'Phù hợp '+a.match_score+'%':'')
      +(a.status==='rejected'&&a.decision_reason?copy('Lý do từ chối: '+a.decision_reason):'')+(a.cv_id?'<a href="/api/applications/'+a.id+'/cv">Xem CV đã nộp</a>':'')+(['pending','reviewing'].includes(a.status)?'<div class="row">'+btn('withdraw','Rút đơn',a.id)+'</div>':''))).join(''):empty())
    +'</div><aside class="split-side"><h2>Lịch phỏng vấn</h2>'+(interviews.length?interviews.map(i=>box('<h3>'+esc(i.location)+'</h3>'+tags(i.scheduled_at.replace('T',' '),status(i.status))
    +copy(i.note)+(i.status==='invited'?form('reply-'+i.id,select('action','Phản hồi',[['confirmed','Xác nhận'],['declined','Từ chối'],['reschedule_requested','Xin đổi lịch']])
      +field('message','Ghi chú / lịch đề xuất'),'Gửi phản hồi'):''))).join(''):empty('Chưa có lời mời.'))+'</aside></div>';
  for(const i of interviews)bindForm(root,'reply-'+i.id,async data=>{await api('/interviews/'+i.id+'/respond',{method:'POST',data});await reload();});
  action(root,'withdraw',async id=>{if(confirm('Rút đơn ứng tuyển này?')){await api('/applications/'+id+'/status',{method:'PATCH',data:{status:'withdrawn'}});await reload();}});
}
export const pages={profile,matching,saved,applications};
