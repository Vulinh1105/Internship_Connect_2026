import {api} from '../api/client.js';
import {esc,tags,box,copy,empty,heading,field,area,select,link,btn,form,grid,money,modes,toast,bindForm,action} from '../components/ui.js';

import {companyGallery} from '../components/company-gallery.js';
import {logoTile, bannerHtml, bindBanner} from '../components/media.js';

const briefcase='<svg aria-hidden="true" width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2M3 13h18m-11 0v2h4v-2"/></svg>';
const searchIcon='<svg aria-hidden="true" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/></svg>';

export const loginRequired=root=>{root.innerHTML=heading('Bạn cần đăng nhập')+link('login','Đăng nhập');};
export function jobCard(j){
  const workMode=modes.find(([key])=>key===j.work_mode)?.[1];
  return '<article class="card job-card"><div class="card-identity"><span class="card-icon">'+briefcase+'</span>'
    +'<span>'+esc(j.company_name)+'</span>'+(j.match_score!=null?'<span class="score card-score">Phù hợp '+esc(j.match_score)+'%</span>':'')
    +'</div><h3><a href="#job/'+j.id+'">'+esc(j.title)+'</a></h3>'
    +tags(j.location,workMode,j.category)
    +'<p class="job-summary">'+esc(money(j.salary_min,j.salary_max))+' · Hạn '+esc(j.deadline||'linh hoạt')+'</p>'
    +(j.reason?'<p>'+esc(j.reason)+'</p>':'')
    +(j.skills?.length?tags(...j.skills.slice(0,5)):'')+'<div class="card-footer"><a class="card-link" href="#job/'+j.id+'">Xem chi tiết <span aria-hidden="true">→</span></a></div></article>';
}
const pinIcon='<svg aria-hidden="true" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/></svg>';
const heartIcon='<svg aria-hidden="true" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/></svg>';
const topCard=j=>'<article class="card top-card"><div class="top-card-head">'+logoTile(j.company_id,j.company_name)
  +'<div><h3><a href="#job/'+j.id+'">'+esc(j.title)+'</a></h3><p class="muted">'+esc(j.company_name)+'</p></div></div>'
  +'<div class="top-card-foot">'+tags(money(j.salary_min,j.salary_max),j.location)
  +'<button type="button" class="heart" data-action="save" data-value="'+j.id+'" aria-label="Lưu tin '+esc(j.title)+'">'+heartIcon+'</button></div></article>';
async function home({root,user}){
  const data=await api('/jobs?limit=100');
  const unique=key=>[...new Set(data.items.map(j=>j[key]).filter(Boolean))];
  const categories=unique('category'), locations=unique('location');
  root.innerHTML='<section class="home-hero" aria-labelledby="hero-title"><h1 id="hero-title">Tìm kỳ thực tập <em>phù hợp.</em></h1>'
    +'<form class="search-pill" id="hero-search"><label class="q">'+searchIcon
    +'<input type="search" name="q" aria-label="Tìm theo vị trí hoặc kỹ năng" placeholder="Ví dụ: Python, Marketing…" maxlength="200"></label>'
    +'<label class="loc">'+pinIcon+'<select name="location" aria-label="Địa điểm"><option value="">Địa điểm</option>'
    +locations.map(l=>'<option value="'+esc(l)+'">'+esc(l)+'</option>').join('')+'</select></label>'
    +'<button type="submit">'+searchIcon+' Tìm kiếm</button></form>'
    +'<div class="hero-panels"><div class="cat-list">'+categories.slice(0,6).map(c=>'<a href="#jobs/'+new URLSearchParams({category:c})+'">'+esc(c)+'<span aria-hidden="true">›</span></a>').join('')+'</div>'
    +bannerHtml()+'</div></section>'
    +'<section class="section" aria-labelledby="latest-title"><div class="section-heading"><div>'
    +'<p class="eyebrow">Cơ hội mới · '+data.total+' vị trí đang mở</p><h2 id="latest-title">Vị trí mới nhất</h2></div>'
    +'<a href="#jobs">Xem tất cả</a></div>'
    +(locations.length?'<div class="chips">'+locations.map(l=>'<a class="chip" href="#jobs/'+new URLSearchParams({location:l})+'">'+esc(l)+'</a>').join('')+'</div>':'')
    +(featured(data).length?'<div class="top-grid">'+featured(data).map(topCard).join('')+'</div>':empty('Hiện chưa có vị trí đang mở.'))
    +'</section>'+companyGallery();
  bindBanner(root);
  bindForm(root,'hero-search',values=>{
    const params=new URLSearchParams(Object.entries(values).map(([k,v])=>[k,v.trim()]).filter(([,v])=>v));
    location.hash=params.toString()?'jobs/'+params:'jobs';
  });
  action(root,'save',async id=>{
    if(!user){location.hash='login';return;}
    await api('/jobs/'+id+'/saved',{method:'PUT'});toast('Đã lưu tin');
  });
}
const featured=data=>data.items.slice(0,6);
async function jobs({root,args,user}){
  const params=new URLSearchParams(args[0]||'');
  const page=await api('/jobs?'+params);
  root.innerHTML=heading('Vị trí thực tập','Chỉ hiển thị các tin đang mở, còn hạn và đã được duyệt.')
    +box(form('search','<div class="form-grid">'+field('q','Từ khóa',params.get('q'))+field('location','Địa điểm',params.get('location'))
    +field('category','Ngành',params.get('category'))+select('work_mode','Hình thức',[['','Tất cả'],...modes],params.get('work_mode'))
    +select('level','Cấp độ',[['','Tất cả'],['intern','Thực tập'],['fresher','Fresher'],['junior','Junior'],['senior','Senior']],params.get('level'))
    +field('salary_min','Lương từ',params.get('salary_min'),'number','min="0"')+field('salary_max','Lương đến',params.get('salary_max'),'number','min="0"')+'</div>','Tìm vị trí'))
    +'<div class="row results-bar"><span class="muted">'+page.total+' kết quả</span>'+(user?link('saved','Tin đã lưu'):'')+'</div>'
    +(page.items.length?grid(page.items.map(jobCard)):empty('Chưa có tin khớp với bộ lọc.'))
    +'<div class="row">'+(page.offset?btn('page','Trang trước',Math.max(0,page.offset-page.limit)):'')
    +(page.offset+page.limit<page.total?btn('page','Trang tiếp',page.offset+page.limit):'')+'</div>';
  bindForm(root,'search',values=>{location.hash='jobs/'+new URLSearchParams(Object.entries(values).filter(([,v])=>v));});
  action(root,'page',offset=>{params.set('offset',offset);location.hash='jobs/'+params;});
}
const levelLabel={intern:'Thực tập',fresher:'Fresher',junior:'Junior',senior:'Senior'};
const scheduleLabel={part_time:'Bán thời gian',full_time:'Toàn thời gian'};
const programLabel={internship:'Thực tập',trainee:'Thực tập sinh'};
const svg=path=>'<svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'+path+'</svg>';
const iconPin=svg('<path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/>');
const iconExp=svg('<circle cx="12" cy="9" r="5"/><path d="m9 13-1 8 4-2 4 2-1-8"/>');
const iconCal=svg('<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M8 3v4M16 3v4M4 10h16"/>');
const bullets=text=>{
  const lines=String(text||'').split('\n').map(s=>s.trim().replace(/^(\d+[.)]|[-•*])\s*/,'')).filter(Boolean);
  return lines.length?'<ul class="bullets">'+lines.map(l=>'<li>'+esc(l)+'</li>').join('')+'</ul>':'';
};
const infoItem=(icon,label,value)=>'<div class="info-item"><span class="info-icon">'+icon+'</span><div><small class="muted">'+esc(label)+'</small><b>'+esc(value)+'</b></div></div>';
const fact=(label,value)=>value?'<div><dt>'+esc(label)+'</dt><dd>'+esc(value)+'</dd></div>':'';
const overviewRow=(label,html)=>html?'<div class="overview-row"><span class="muted">'+esc(label)+'</span>'+html+'</div>':'';
async function job({root,args,user}){
  const j=await api('/jobs/'+Number(args[0]));
  const c=await api('/companies/'+j.company_id).catch(()=>null);
  const d=j.details||{}, cd=c?.details||{};
  const canApply=user?.role==='student'&&j.active;
  const workMode=modes.find(([key])=>key===j.work_mode)?.[1];
  root.innerHTML='<p class="crumbs"><a href="#home">Trang chủ</a> › <a href="#jobs">Vị trí thực tập</a> › '+esc(j.title)+'</p><div class="detail-layout"><div class="detail-main">'
    +box('<h1>'+esc(j.title)+'</h1><p class="salary">'+esc(money(j.salary_min,j.salary_max))+'</p>'
      +'<div class="info-trio">'+infoItem(iconPin,'Địa điểm',j.location)+infoItem(iconExp,'Kinh nghiệm',d.experience||'—')+infoItem(iconCal,'Hạn ứng tuyển',j.deadline||'Linh hoạt')+'</div>'
      +'<div class="cta-row">'+(canApply?'<button type="button" data-action="goto-apply">Ứng tuyển ngay</button>':!user?'<a class="button" href="#login">Đăng nhập để ứng tuyển</a>':'')
      +(user&&j.active?btn('save','Lưu tin'):'')+'</div>')
    +box('<h2 class="section-title">Tổng quan</h2>'+overviewRow('Kỹ năng',j.skills?.length?tags(...j.skills):'')+overviewRow('Ngành',tags(j.category))
      +overviewRow('Hình thức',tags(workMode))+overviewRow('Thời gian',d.working_hours?tags(d.working_hours):''))
    +box('<h2 class="section-title">Mô tả công việc</h2>'+bullets(j.description)+'<h2 class="section-title">Yêu cầu</h2>'+bullets(j.requirements)
      +(d.benefits?'<h2 class="section-title">Quyền lợi</h2>'+bullets(d.benefits):''))
    +'</div><aside class="detail-side">'
    +box('<div class="company-head">'+logoTile(j.company_id,j.company_name,true)+'<h3>'+esc(j.company_name)+'</h3></div>'
      +'<div class="company-facts">'+(cd.company_size?'<p><b>Quy mô:</b> '+esc(cd.company_size)+' nhân viên</p>':'')
      +((cd.address||c?.city)?'<p><b>Địa điểm:</b> '+esc(cd.address||c.city)+'</p>':'')+(c?.industry?'<p><b>Ngành nghề:</b> '+esc(c.industry)+'</p>':'')+'</div>'
      +link('company/'+j.company_id,'Xem trang công ty')).replace('class="panel"','class="panel company-card"')
    +box('<h2 class="section-title">Thông tin chung</h2><dl class="facts">'+fact('Cấp bậc',levelLabel[j.level]||j.level)+fact('Học vấn',d.education)
      +fact('Số lượng tuyển',d.quantity?d.quantity+' người':'')+fact('Hình thức làm việc',workMode)
      +fact('Loại hình',[scheduleLabel[d.employment_schedule],programLabel[d.program_type]].filter(Boolean).join(' · '))+'</dl>')
    +'</aside></div>';
  action(root,'save',async()=>{await api('/jobs/'+j.id+'/saved',{method:'PUT'});toast('Đã lưu tin');});
  action(root,'goto-apply',()=>root.querySelector('#apply-section')?.scrollIntoView({behavior:'smooth'}));
  if(canApply){
    const cvs=await api('/students/me/cvs');
    root.querySelector('.detail-main').insertAdjacentHTML('beforeend','<div id="apply-section">'+box('<h2 class="section-title">Ứng tuyển</h2>'+form('apply',select('cv_id','CV',[['','Dùng hồ sơ hiện tại'],...cvs.map(c=>[c.id,c.original_name])])
      +area('cover_letter','Thư ứng tuyển','','maxlength="5000"'),'Gửi đơn'))+'</div>');
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
  root.innerHTML='<div class="auth">'+heading('Đăng nhập','Dùng tài khoản đã kích hoạt trong bộ dữ liệu hoặc đăng ký sinh viên.')
    +box(form('login',field('email','Email','','email','required autocomplete="username"')+field('password','Mật khẩu','','password','required autocomplete="current-password"'),'Đăng nhập'))
    +box('<h2>Tài khoản mẫu</h2><p class="muted">Dùng mật khẩu demo đã đặt khi seed. Mặc định LocalDemo2026!</p><div class="row">'
    +[['usr-demo-s001','Sinh viên'],['usr-demo-c001','Doanh nghiệp'],['staff-demo','Kiểm duyệt'],['admin-demo','Admin']].map(([k,v])=>btn('demo',v,k+'@example.invalid')).join('')
    +'</div>')+link('register','Đăng ký sinh viên')+'</div>';
  action(root,'demo',email=>{root.querySelector('#login [name=email]').value=email;root.querySelector('#login [name=password]').focus();});
  bindForm(root,'login',async data=>{await api('/auth/login',{method:'POST',data});location.hash='home';});
}
async function register({root}){
  root.innerHTML='<div class="auth">'+heading('Đăng ký sinh viên')+box(form('register',field('name','Họ tên','','text','required')+field('email','Email','','email','required')
    +field('password','Mật khẩu','','password','required minlength="8" autocomplete="new-password"'),'Tạo tài khoản'))+'</div>';
  bindForm(root,'register',async data=>{await api('/auth/register',{method:'POST',data});location.hash='profile';});
}
export const pages={home,jobs,job,companies,company,login,register};
