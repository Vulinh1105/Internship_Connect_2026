import {api} from '../api/client.js';
import {esc,tags,box,copy,empty,heading,field,area,select,link,btn,form,grid,list,money,modes,status,toast,bindForm,action} from '../components/ui.js';
import {companyCard,jobCard,loginRequired} from './public.js';

const cvFile='<label class="field">Tệp .pdf, .docx hoặc .txt (tối đa 5 MB)<input type="file" name="file" required accept=".pdf,application/pdf,.docx,.txt"></label>';

async function profile({root,user,reload}){
  if(!user)return loginRequired(root);
  const [cvs,profile]=await Promise.all([api('/students/me/cvs'),api('/students/me')]);
  const d=profile.details||{}, p=profile.preferences||{};
  root.innerHTML=heading('Hồ sơ nghề nghiệp','Thông tin dùng khi ứng tuyển và tìm việc. AI Matching ưu tiên kỹ năng đọc được từ CV đã xác nhận.')
    +box(form('career','<div class="form-grid">'
      +field('name','Họ tên',profile.name,'text','required maxlength="150"')+field('school','Trường',d.school)
      +field('major','Ngành',profile.major)+field('specialization','Chuyên ngành',d.specialization)
      +field('study_year','Năm học',d.study_year,'number','min="1" max="10"')
      +field('target_category','Vị trí mong muốn',p.target_category)+field('preferred_location','Địa điểm mong muốn',p.preferred_location)
      +select('preferred_work_mode','Hình thức làm việc',[['','Linh hoạt'],...modes],p.preferred_work_mode)
      +field('salary_min','Lương kỳ vọng tối thiểu',p.salary_min,'number','min="0"')
      +select('level','Cấp độ',[['intern','Thực tập'],['fresher','Fresher'],['junior','Junior']],p.level)
      +'</div>'+area('summary','Giới thiệu',profile.summary,'maxlength="4000"')
      +area('skills','Kỹ năng (cách nhau bằng dấu phẩy hoặc xuống dòng)',(profile.profile_skills||[]).join(', '),
        'rows="3" placeholder="Ví dụ: Python, Docker, Kubernetes"'),'Lưu hồ sơ nghề nghiệp'))
    +box('<h2>Tải CV</h2>'+form('upload',cvFile,'Tải lên'))
    +cvs.map(c=>box('<h3>'+esc(c.original_name)+'</h3>'
      +tags(c.confirmed?'Sẵn sàng sử dụng':'Chờ xác nhận')
      +(c.has_text===false?copy('Có thể đính kèm CV khi ứng tuyển. Gợi ý theo nội dung cần CV có văn bản đọc được.'):'')
      +'<div class="row"><a href="/api/students/me/cvs/'+c.id+'/download">Tải bản gốc</a>'
      +(!c.confirmed?btn('activate-cv','Dùng CV này',c.id):'')+btn('remove-cv','Xóa CV',c.id)+'</div>'
      +'<details><summary>Thay CV</summary>'+form('replace-'+c.id,cvFile,'Lưu CV mới')+'</details>')).join('');
  bindForm(root,'career',async data=>{
    const skills=[...new Set(list(data.skills))];
    if(skills.length>40)throw new Error('Bạn có thể nhập tối đa 40 kỹ năng.');
    const {name,major,school,specialization,study_year,summary,target_category,preferred_location,preferred_work_mode,salary_min,level}=data;
    await api('/students/me',{method:'PUT',data:{name,major,school,specialization,study_year:Number(study_year)||null,
      summary,skills,
      preferences:{target_category,preferred_location,preferred_work_mode,salary_min:salary_min===''?null:Number(salary_min),level}}});
    toast('Đã lưu hồ sơ nghề nghiệp');await reload();
  });
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
const matchCriteria=[['skills','Kỹ năng',40],['semantic','Ngữ nghĩa',25],['major','Ngành học',10],
  ['experience','Kinh nghiệm và dự án',10],['preferences','Nguyện vọng',15]];
const matchRow=j=>{
  const pct=Math.max(0,Math.min(100,Math.round(Number(j.match_score)||0)));
  const workMode=modes.find(([key])=>key===j.work_mode)?.[1];
  return '<article class="card match-row"><div class="ring" style="--pct:'+pct+'" role="img" aria-label="'+(j.match_score!=null?'Phù hợp '+pct+'%':'Chưa có điểm')+'"><span>'+(j.match_score!=null?pct+'%':'–')+'</span></div>'
    +'<div class="match-body"><h3><a href="#job/'+j.id+'">'+esc(j.title)+'</a></h3><p class="muted">'+esc(j.company_name)+'</p>'
    +tags(j.location,workMode,j.category)
    +'<p class="job-summary">'+esc(money(j.salary_min,j.salary_max))+' · Hạn '+esc(j.deadline||'linh hoạt')+'</p>'
    +(j.reason?'<p>'+esc(j.reason)+'</p>':'')
    +'<details><summary>Chi tiết điểm phù hợp</summary>'
    +copy('Kỹ năng đã có: '+(j.matched_skills?.join(', ')||'Chưa ghi nhận'))
    +copy('Kỹ năng còn thiếu: '+(j.missing_skills?.join(', ')||'Không có'))
    +matchCriteria.map(([key,label,max])=>copy(label+': '+(key==='semantic'&&!j.semantic_available?'Chờ đồng bộ':(j.score_breakdown?.[key]??0)+'/'+max))).join('')
    +'</details></div>'
    +'<a class="card-link" href="#job/'+j.id+'">Xem thêm <span aria-hidden="true">→</span></a></article>';
};
async function matching({root,user}){
  if(!user)return loginRequired(root);
  const jobs=await api('/matching');
  root.innerHTML=heading('AI Matching','Xếp hạng theo hồ sơ và CV đã xác nhận. OpenAI tạo vector từ văn bản hồ sơ đã lọc thông tin liên hệ, và hệ thống tính điểm theo từng tiêu chí.')
    +(jobs.length?'<div class="match-list">'+jobs.map(matchRow).join('')+'</div>':empty())+(!jobs.length?link('profile','Cập nhật hồ sơ'):'');
}
async function saved({root,user,reload}){
  if(!user)return loginRequired(root);
  const jobs=await api('/jobs/saved');
  const labels={open:'Còn tuyển',closed:'Đã đóng',expired:'Hết hạn',removed:'Đã gỡ'};
  root.innerHTML=heading('Tin đã lưu')+grid(jobs.map(j=>box((j.saved_status==='open'?jobCard(j):'<h3>'+esc(j.title)+'</h3>')
    +tags(labels[j.saved_status],j.deadline?'Hạn '+j.deadline:'Hạn linh hoạt')+btn('remove','Bỏ lưu',j.id))));
  action(root,'remove',async id=>{await api('/jobs/'+id+'/saved?value=false',{method:'PUT'});await reload();});
}
async function applications({root,user,reload}){
  if(!user)return loginRequired(root);
  const [apps,interviews]=await Promise.all([api('/applications/me'),api('/interviews')]);
  root.innerHTML=heading('Đơn ứng tuyển','Theo dõi trạng thái và phản hồi lời mời phỏng vấn trên web.')
    +'<div class="split"><div class="split-main"><h2>Đơn của bạn</h2>'+(apps.length?apps.map(a=>box('<h3>'+esc(a.job_title)+'</h3>'+tags('#'+a.id,status(a.status),a.match_score!=null?'Phù hợp '+a.match_score+'%':'')
      +(a.completed_at?tags('Đã hoàn thành kỳ thực tập'):'')
      +(a.review_status?tags(({pending:'Đánh giá đang chờ duyệt',approved:'Đánh giá đã công khai',rejected:'Đánh giá bị từ chối'})[a.review_status]):'')
      +(a.completed_at&&!a.review_status?form('review-'+a.id,select('rating','Điểm doanh nghiệp',Array.from({length:5},(_,i)=>[i+1,(i+1)+'/5']),'5')
        +area('note','Đánh giá kỳ thực tập','','required maxlength="2000"'),'Gửi đánh giá'):'')
      +(a.status==='rejected'&&a.decision_reason?copy('Lý do từ chối: '+a.decision_reason):'')+(a.cv_id?'<a href="/api/applications/'+a.id+'/cv">Xem CV đã nộp</a>':'')+(['pending','reviewing'].includes(a.status)?'<div class="row">'+btn('withdraw','Rút đơn',a.id)+'</div>':''))).join(''):empty())
    +'</div><aside class="split-side"><h2>Lịch phỏng vấn</h2>'+(interviews.length?interviews.map(i=>box('<h3>'+esc(i.location)+'</h3>'+tags(i.scheduled_at.replace('T',' '),status(i.status))
    +copy(i.note)+(i.status==='invited'?form('reply-'+i.id,select('action','Phản hồi',[['confirmed','Xác nhận'],['declined','Từ chối'],['reschedule_requested','Xin đổi lịch']])
      +field('message','Ghi chú / lịch đề xuất'),'Gửi phản hồi'):''))).join(''):empty('Chưa có lời mời.'))+'</aside></div>';
  for(const a of apps)bindForm(root,'review-'+a.id,async data=>{
    await api('/applications/'+a.id+'/company-review',{method:'POST',data:{rating:Number(data.rating),note:data.note}});
    toast('Đánh giá đang chờ duyệt');await reload();
  });
  for(const i of interviews)bindForm(root,'reply-'+i.id,async data=>{await api('/interviews/'+i.id+'/respond',{method:'POST',data});await reload();});
  action(root,'withdraw',async id=>{if(confirm('Rút đơn ứng tuyển này?')){await api('/applications/'+id+'/status',{method:'PATCH',data:{status:'withdrawn'}});await reload();}});
}
async function followed({root,user,reload}){
  if(!user)return loginRequired(root);
  const rows=await api('/companies/followed');
  const industries=[...new Set(rows.map(c=>c.industry).filter(Boolean))].sort();
  root.innerHTML=heading('Doanh nghiệp đang theo dõi')
    +select('industry','Lĩnh vực',[['','Tất cả'],...industries.map(x=>[x,x])])+'<div id="followed-list"></div>';
  const list=root.querySelector('#followed-list');
  const filter=root.querySelector('[name="industry"]');
  function paint(){
    list.innerHTML=grid(rows.filter(c=>!filter.value||c.industry===filter.value).map(c=>
      box(companyCard(c)+tags(c.active_jobs+' tin đang tuyển')+btn('unfollow','Bỏ theo dõi',c.id))));
    action(list,'unfollow',async id=>{await api('/companies/'+id+'/follow?value=false',{method:'PUT'});await reload();});
  }
  filter.addEventListener('change',paint);
  paint();
}
export const pages={profile,matching,saved,applications,followed};
