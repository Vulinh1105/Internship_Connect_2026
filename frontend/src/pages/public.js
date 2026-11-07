import {api} from '../api/client.js';
import {esc,tags,box,copy,empty,heading,field,area,select,link,btn,form,grid,money,modes,toast,bindForm,action} from '../components/ui.js';

import {companyGallery, heroPhoto} from '../components/company-gallery.js';

const briefcase='<svg aria-hidden="true" width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2M3 13h18m-11 0v2h4v-2"/></svg>';
const searchIcon='<svg aria-hidden="true" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/></svg>';

export const loginRequired=root=>{root.innerHTML=heading('Bạn cần đăng nhập')+link('login','Đăng nhập');};
export function jobCard(j){
  const workMode=modes.find(([key])=>key===j.work_mode)?.[1];
  return '<article class="card job-card"><div class="card-identity"><span class="card-icon">'+briefcase+'</span>'
    +'<span>'+esc(j.company_name)+'</span></div><h3><a href="#job/'+j.id+'">'+esc(j.title)+'</a></h3>'
    +tags(j.location,workMode,j.category)
    +'<p class="job-summary">'+esc(money(j.salary_min,j.salary_max))+' · Hạn '+esc(j.deadline||'linh hoạt')+'</p>'
    +(j.match_score!=null?'<p class="score">Phù hợp '+esc(j.match_score)+'%</p>':'')
    +(j.reason?'<p>'+esc(j.reason)+'</p>':'')
    +(j.skills?.length?tags(...j.skills.slice(0,5)):'')+link('job/'+j.id,'Xem chi tiết')+'</article>';
}
async function home({root}){
  const data=await api('/jobs?limit=6');
  root.innerHTML='<section class="hero" aria-labelledby="hero-title"><div class="hero-copy">'
    +'<p class="eyebrow">Thực tập · Hồ sơ · Phỏng vấn</p>'
    +'<h1 id="hero-title">Tìm kỳ thực tập <em>phù hợp.</em></h1>'
    +'<p>Khám phá tin đang tuyển, chuẩn bị CV và theo dõi từng bước ứng tuyển.</p>'
    +'<form class="hero-search" id="hero-search"><label>'+searchIcon
    +'<input type="search" name="q" aria-label="Tìm theo vị trí hoặc kỹ năng" placeholder="Ví dụ: Python, Marketing…" maxlength="200"></label>'
    +'<button type="submit">Tìm thực tập <span aria-hidden="true">↗</span></button></form>'
    +'<div class="hero-stats"><strong>'+data.total+'</strong><span>vị trí đang mở</span></div></div>'
    +heroPhoto()+'</section>'
    +'<section class="section" aria-labelledby="latest-title"><div class="section-heading"><div>'
    +'<p class="eyebrow">Cơ hội mới</p><h2 id="latest-title">Vị trí mới nhất</h2></div>'
    +link('jobs','Tất cả vị trí ↗')+'</div>'
    +(data.items.length?grid(data.items.map(jobCard)):empty('Hiện chưa có vị trí đang mở.'))
    +'</section>'+companyGallery();
  bindForm(root,'hero-search',({q})=>{
    const query=q.trim();
    location.hash=query?'jobs/'+new URLSearchParams({q:query}):'jobs';
  });
}
async function jobs({root,args,user}){
  const params=new URLSearchParams(args[0]||'');
  const page=await api('/jobs?'+params);
  root.innerHTML=heading('Vị trí thực tập','Chỉ hiển thị các tin đang mở, còn hạn và đã được duyệt.')
    +box(form('search','<div class="form-grid">'+field('q','Từ khóa',params.get('q'))+field('location','Địa điểm',params.get('location'))
    +field('category','Ngành',params.get('category'))+select('work_mode','Hình thức',[['','Tất cả'],...modes],params.get('work_mode'))
    +select('level','Cấp độ',[['','Tất cả'],['intern','Thực tập'],['fresher','Fresher'],['junior','Junior'],['senior','Senior']],params.get('level'))
    +field('salary_min','Lương từ',params.get('salary_min'),'number','min="0"')+field('salary_max','Lương đến',params.get('salary_max'),'number','min="0"')+'</div>','Tìm vị trí'))
    +'<div class="row"><span class="muted">'+page.total+' kết quả</span>'+(user?link('saved','Tin đã lưu'):'')+'</div>'
    +(page.items.length?grid(page.items.map(jobCard)):empty('Chưa có tin khớp với bộ lọc.'))
    +'<div class="row">'+(page.offset?btn('page','Trang trước',Math.max(0,page.offset-page.limit)):'')
    +(page.offset+page.limit<page.total?btn('page','Trang tiếp',page.offset+page.limit):'')+'</div>';
  bindForm(root,'search',values=>{location.hash='jobs/'+new URLSearchParams(Object.entries(values).filter(([,v])=>v));});
  action(root,'page',offset=>{params.set('offset',offset);location.hash='jobs/'+params;});
}
async function job({root,args,user}){
  const j=await api('/jobs/'+Number(args[0]));
  root.innerHTML=heading(j.title,j.company_name)+tags(j.category,j.location,j.work_mode,money(j.salary_min,j.salary_max),j.deadline&&'Hạn '+j.deadline)
    +box('<h2>Mô tả công việc</h2>'+copy(j.description)+'<h2>Yêu cầu</h2>'+copy(j.requirements)+tags(...j.skills)
    +(j.details?.benefits?'<h2>Quyền lợi</h2>'+copy(j.details.benefits):''))
    +'<div class="row">'+link('company/'+j.company_id,'Xem doanh nghiệp')+(user&&j.active?btn('save','Lưu tin'):'')
    +(!user?link('login','Đăng nhập để ứng tuyển'):'')+'</div>';
  action(root,'save',async()=>{await api('/jobs/'+j.id+'/saved',{method:'PUT'});toast('Đã lưu tin');});
  if(user?.role==='student'&&j.active){
    const cvs=await api('/students/me/cvs');
    root.insertAdjacentHTML('beforeend',box('<h2>Ứng tuyển</h2>'+form('apply',select('cv_id','CV',[['','Dùng hồ sơ hiện tại'],...cvs.map(c=>[c.id,c.original_name])])
      +area('cover_letter','Thư ứng tuyển','','maxlength="5000"'),'Gửi đơn')));
    bindForm(root,'apply',async values=>{
      await api('/applications',{method:'POST',data:{...values,job_id:j.id,cv_id:Number(values.cv_id)||null}});
      toast('Đã gửi đơn');location.hash='applications';
    });
  }
}
const companyCard=c=>'<article class="card"><h3><a href="#company/'+c.id+'">'+esc(c.name)+'</a></h3>'+tags(c.industry,c.city)+copy(c.description.slice(0,170)+'…')+'</article>';
async function companies({root}){
  const records=await api('/companies');
  root.innerHTML=heading('Doanh nghiệp','Khám phá hồ sơ trong hệ thống và xem ảnh những địa điểm làm việc tại Việt Nam.')
    +companyGallery()+'<section class="section" aria-labelledby="demo-companies-title">'
    +'<div class="section-heading"><div><p class="eyebrow">Dữ liệu ứng tuyển mẫu</p>'
    +'<h2 id="demo-companies-title">Doanh nghiệp trên hệ thống</h2></div></div>'
    +grid(records.map(companyCard))+'</section>';
}
async function company({root,args,user}){
  const c=await api('/companies/'+Number(args[0]));
  root.innerHTML=heading(c.name,c.industry)+tags(c.city,c.details?.company_size,c.details?.verification_status)
    +box(copy(c.description)+copy(c.details?.culture||'')+copy(c.details?.benefits||''))
    +(user?'<div class="row">'+btn('follow','Theo dõi')+btn('unfollow','Bỏ theo dõi')+'</div>':'');
  for(const [name,value] of [['follow',true],['unfollow',false]])action(root,name,async()=>{
    await api('/companies/'+c.id+'/follow?value='+value,{method:'PUT'});toast(value?'Đã theo dõi':'Đã bỏ theo dõi');
  });
}
async function login({root,user}){
  if(user){root.innerHTML=heading('Bạn đã đăng nhập',user.email)+link('home','Trang chủ');return;}
  root.innerHTML=heading('Đăng nhập','Dùng tài khoản đã kích hoạt trong bộ dữ liệu hoặc đăng ký sinh viên.')
    +'<div class="narrow">'+box(form('login',field('email','Email','','email','required autocomplete="username"')+field('password','Mật khẩu','','password','required autocomplete="current-password"'),'Đăng nhập'))
    +box('<h2>Tài khoản mẫu</h2><p class="muted">Dùng mật khẩu demo đã đặt khi seed. Mặc định LocalDemo2026!</p><div class="row">'
    +[['usr-demo-s001','Sinh viên'],['usr-demo-c001','Doanh nghiệp'],['staff-demo','Kiểm duyệt'],['admin-demo','Admin']].map(([k,v])=>btn('demo',v,k+'@example.invalid')).join('')
    +'</div>')+link('register','Đăng ký sinh viên')+'</div>';
  action(root,'demo',email=>{root.querySelector('#login [name=email]').value=email;root.querySelector('#login [name=password]').focus();});
  bindForm(root,'login',async data=>{await api('/auth/login',{method:'POST',data});location.hash='home';});
}
async function register({root}){
  root.innerHTML=heading('Đăng ký sinh viên')+box(form('register',field('name','Họ tên','','text','required')+field('email','Email','','email','required')
    +field('password','Mật khẩu','','password','required minlength="8" autocomplete="new-password"'),'Tạo tài khoản'));
  bindForm(root,'register',async data=>{await api('/auth/register',{method:'POST',data});location.hash='profile';});
}
export const pages={home,jobs,job,companies,company,login,register};
