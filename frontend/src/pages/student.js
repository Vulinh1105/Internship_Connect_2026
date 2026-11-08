import {api} from '../api/client.js';
import {esc,tags,box,copy,empty,heading,field,select,link,btn,form,grid,status,toast,bindForm,action} from '../components/ui.js';
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
async function matching({root,user}){
  if(!user)return loginRequired(root);
  const jobs=await api('/matching');
  root.innerHTML=heading('AI Matching','Gợi ý dựa trên hồ sơ, kỹ năng và nguyện vọng. Điểm số dùng để tham khảo khi chọn tin.')
    +grid(jobs.map(jobCard))+(!jobs.length?link('profile','Cập nhật hồ sơ'):'');
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
    +'<h2>Lịch phỏng vấn</h2>'+(interviews.length?interviews.map(i=>box('<h3>'+esc(i.location)+'</h3>'+tags(i.scheduled_at.replace('T',' '),status(i.status))
    +copy(i.note)+(i.status==='invited'?form('reply-'+i.id,select('action','Phản hồi',[['confirmed','Xác nhận'],['declined','Từ chối'],['reschedule_requested','Xin đổi lịch']])
      +field('message','Ghi chú / lịch đề xuất'),'Gửi phản hồi'):''))).join(''):empty('Chưa có lời mời.'))
    +'<h2>Đơn của bạn</h2>'+(apps.length?apps.map(a=>box('<h3>'+esc(a.job_title)+'</h3>'+tags('#'+a.id,status(a.status),a.match_score!=null?'Phù hợp '+a.match_score+'%':'')
      +(a.cv_id?'<a href="/api/applications/'+a.id+'/cv">Xem CV đã nộp</a>':'')+(['pending','reviewing'].includes(a.status)?'<div class="row">'+btn('withdraw','Rút đơn',a.id)+'</div>':''))).join(''):empty());
  for(const i of interviews)bindForm(root,'reply-'+i.id,async data=>{await api('/interviews/'+i.id+'/respond',{method:'POST',data});await reload();});
  action(root,'withdraw',async id=>{if(confirm('Rút đơn ứng tuyển này?')){await api('/applications/'+id+'/status',{method:'PATCH',data:{status:'withdrawn'}});await reload();}});
}
async function notifications({root,user,reload}){
  if(!user)return loginRequired(root);
  const rows=await api('/notifications');
  root.innerHTML=heading('Thông báo')+btn('read','Đánh dấu đã đọc')+(rows.length?rows.map(n=>box(tags(n.read_at?'Đã đọc':'Mới',n.created_at.replace('T',' ').slice(0,16))+copy(n.message))).join(''):empty());
  action(root,'read',async()=>{await api('/notifications/read',{method:'POST'});await reload();});
}
export const pages={profile,matching,saved,applications,notifications};
