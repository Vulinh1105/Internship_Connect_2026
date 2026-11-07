import {api} from '../api/client.js';
import {esc,tags,box,copy,empty,heading,field,area,select,link,btn,form,grid,modes,list,status,toast,bindForm,action} from '../components/ui.js';
import {jobCard,loginRequired} from './public.js';

const facts=[['skills','Kỹ năng'],['education','Học vấn'],['experience','Kinh nghiệm'],['projects','Dự án'],['certificates','Chứng chỉ'],['languages','Ngoại ngữ']];
const lineList=value=>String(value||'').split('\n').map(s=>s.trim()).filter(Boolean);
async function profile({root,user,reload}){
  if(!user)return loginRequired(root);
  const [p,cvs,catalog]=await Promise.all([api('/students/me'),api('/students/me/cvs'),api('/students/skills')]);
  const pref=p.preferences;
  root.innerHTML=heading('Hồ sơ & CV','Kiểm tra dữ liệu trích xuất trước khi đưa vào gợi ý vị trí.')
    +box(form('profile','<div class="form-grid">'+field('name','Họ tên',p.name,'text','required')+field('major','Chuyên ngành',p.major)
    +field('target_category','Ngành muốn làm',pref.target_category)+field('preferred_location','Địa điểm mong muốn',pref.preferred_location)
    +select('preferred_work_mode','Hình thức',[['','Linh hoạt'],...modes],pref.preferred_work_mode)
    +field('salary_min','Lương tối thiểu',pref.salary_min,'number','min="0"')+'</div>'
    +field('skills','Kỹ năng, cách nhau bằng dấu phẩy',p.skills.join(', '))
    +area('summary','Giới thiệu',p.summary),'Lưu hồ sơ')
    +'<details><summary>Danh mục kỹ năng</summary>'+tags(...catalog.map(s=>s.name))+'</details>')
    +box('<h2>Tải CV</h2>'+form('upload','<label class="field">PDF, DOCX hoặc TXT tối đa 5 MB<input type="file" name="file" required accept=".pdf,.docx,.txt"></label>'
    +'<label><input type="checkbox" name="ai_consent" value="true"> Cho phép dùng mô hình AI để trích xuất văn bản đã lọc thông tin liên hệ</label>','Tải lên'))
    +cvs.map(c=>box('<h3>'+esc(c.original_name)+'</h3>'+tags(c.confirmed?'Đã xác nhận':'Chờ xác nhận')
      +'<a href="/api/students/me/cvs/'+c.id+'/download">Tải bản gốc</a><details '+(!c.confirmed?'open':'')+'><summary>Kiểm tra và chỉnh dữ liệu</summary>'
      +form('cv-'+c.id,facts.map(([key,label])=>area(key,label,(c.extracted[key]||[]).join('\n'))).join(''),'Xác nhận dữ liệu')+'</details>')).join('');
  bindForm(root,'profile',async data=>{
    const {name,major,summary,skills,salary_min,...preferences}=data;
    await api('/students/me',{method:'PUT',data:{name,major,summary,skills:list(skills),preferences:{...preferences,salary_min:salary_min?Number(salary_min):null}}});
    toast('Đã lưu hồ sơ');await reload();
  });
  bindForm(root,'upload',async data=>{await api('/students/me/cvs',{method:'POST',data});toast('Hãy kiểm tra dữ liệu CV');await reload();},{keepFiles:true});
  for(const c of cvs)bindForm(root,'cv-'+c.id,async values=>{
    await api('/students/me/cvs/'+c.id+'/confirm',{method:'POST',data:Object.fromEntries(Object.entries(values).map(([k,v])=>[k,lineList(v)]))});
    toast('Đã xác nhận CV');await reload();
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
