import {api} from '../api/client.js';
import {esc,tags,box,copy,empty,heading,field,area,select,link,btn,form,grid,money,modes,toast,bindForm,action} from '../components/ui.js';

import {logoTile, companyPhoto, bannerHtml, bindBanner} from '../components/media.js?v=company-symbols-1';
import {savedIds, heartButton, saveButton, bindHearts} from '../components/saved.js';

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
const pager=(cur,pages,prev,next)=>pages<2?'':'<div class="pager"><button type="button" class="pager-btn" data-action="page" data-value="'+prev+'" aria-label="Trang trước"'+(cur<2?' disabled':'')+'>‹</button>'
  +'<span><b>'+cur+'</b> / '+pages+' trang</span><button type="button" class="pager-btn" data-action="page" data-value="'+next+'" aria-label="Trang sau"'+(cur>=pages?' disabled':'')+'>›</button></div>';
const topCard=ids=>j=>'<article class="card top-card"><div class="top-card-head">'+logoTile(j.company_id,j.company_name,false,j.company_has_logo)
  +'<div><h3><a href="#job/'+j.id+'">'+esc(j.title)+'</a></h3><p class="muted">'+esc(j.company_name)+'</p></div></div>'
  +'<div class="top-card-foot">'+tags(money(j.salary_min,j.salary_max),j.location)
  +heartButton(j.id,j.title,ids.has(j.id))+'</div></article>';
async function home({root,user}){
  const [data,ids]=await Promise.all([api('/jobs?limit=100'),savedIds(user)]);
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
    +(featured(data).length?'<div class="top-grid">'+featured(data).map(topCard(ids)).join('')+'</div>':empty('Hiện chưa có vị trí đang mở.'))
    +'</section>';
  bindBanner(root);
  bindForm(root,'hero-search',values=>{
    const params=new URLSearchParams(Object.entries(values).map(([k,v])=>[k,v.trim()]).filter(([,v])=>v));
    location.hash=params.toString()?'jobs/'+params:'jobs';
  });
  bindHearts(root,user,ids);
}
const featured=data=>data.items.slice(0,6);
async function jobs({root,args,user}){
  const params=new URLSearchParams(args[0]||'');
  const semantic=user&&params.get('search_mode')==='semantic'&&(params.get('q')||'').trim().length>=2;
  const request=semantic?api('/jobs/semantic?'+params).then(items=>({items,total:items.length,offset:0,limit:5})):api('/jobs?'+params);
  const [page,ids]=await Promise.all([request,savedIds(user)]);
  root.innerHTML=heading('Vị trí thực tập','Chỉ hiển thị các tin đang mở, còn hạn và đã được duyệt.')
    +box(form('search','<div class="form-grid">'+(user?select('search_mode','Kiểu tìm kiếm',[['keyword','Theo từ khóa'],['semantic','Theo câu tự nhiên']],params.get('search_mode')):'')
    +field('q','Từ khóa hoặc câu mô tả vị trí',params.get('q'),'text','maxlength="500"')+field('location','Địa điểm',params.get('location'))
    +field('category','Ngành',params.get('category'))+select('work_mode','Hình thức',[['','Tất cả'],...modes],params.get('work_mode'))
    +select('level','Cấp độ',[['','Tất cả'],['intern','Thực tập'],['fresher','Fresher'],['junior','Junior'],['senior','Senior']],params.get('level'))
    +field('salary_min','Lương từ',params.get('salary_min'),'number','min="0"')+field('salary_max','Lương đến',params.get('salary_max'),'number','min="0"')+'</div>','Tìm vị trí'))
    +'<div class="row results-bar"><span class="muted">'+page.total+' kết quả</span>'+(user?link('saved','Tin đã lưu'):'')+'</div>'
    +(page.items.length?'<div class="top-grid">'+page.items.map(topCard(ids)).join('')+'</div>':empty('Chưa có tin khớp với bộ lọc.'))
    +pager(Math.floor(page.offset/page.limit)+1,Math.ceil(page.total/page.limit),Math.max(0,page.offset-page.limit),page.offset+page.limit);
  bindForm(root,'search',values=>{
    if(values.search_mode==='semantic'&&values.q.trim().length<2)throw new Error('Nhập câu mô tả vị trí muốn tìm.');
    location.hash='jobs/'+new URLSearchParams(Object.entries(values).filter(([,v])=>v));
  });
  action(root,'page',offset=>{params.set('offset',offset);location.hash='jobs/'+params;});
  bindHearts(root,user,ids);
}
const levelLabel={intern:'Thực tập',fresher:'Fresher',junior:'Junior',senior:'Senior'};
const scheduleLabel={part_time:'Bán thời gian',full_time:'Toàn thời gian'};
const svg=path=>'<svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'+path+'</svg>';
const iconPin=svg('<path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/>');
const iconExp=svg('<circle cx="12" cy="9" r="5"/><path d="m9 13-1 8 4-2 4 2-1-8"/>');
const iconCal=svg('<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M8 3v4M16 3v4M4 10h16"/>');
const bullets=text=>{
  const lines=String(text||'').split('\n').map(s=>s.trim().replace(/^(\d+[.)]|[-•*])\s*/,'')).filter(Boolean);
  return lines.length?'<ul class="bullets">'+lines.map(l=>'<li>'+esc(l)+'</li>').join('')+'</ul>':'';
};
const benefitList=details=>Array.isArray(details.benefit_groups)&&details.benefit_groups.length
  ?'<ul class="bullets">'+details.benefit_groups.map(b=>'<li><b>'+esc(b.title)+'</b> · '+esc(b.detail)+'</li>').join('')+'</ul>':'';
const infoItem=(icon,label,value)=>'<div class="info-item"><span class="info-icon">'+icon+'</span><div><small class="muted">'+esc(label)+'</small><b>'+esc(value)+'</b></div></div>';
const fact=(label,value)=>value?'<div><dt>'+esc(label)+'</dt><dd>'+esc(value)+'</dd></div>':'';
const overviewRow=(label,html)=>html?'<div class="overview-row"><span class="muted">'+esc(label)+'</span>'+html+'</div>':'';
async function job({root,args,user}){
  const j=await api('/jobs/'+Number(args[0]));
  if(j.active)api('/jobs/'+j.id+'/views',{method:'POST'}).catch(()=>{});
  const [c,ids]=await Promise.all([api('/companies/'+j.company_id).catch(()=>null),savedIds(user)]);
  const d=j.details||{}, cd=c?.details||{};
  const canApply=user?.role==='student'&&j.active;
  const workMode=modes.find(([key])=>key===j.work_mode)?.[1];
  root.innerHTML='<p class="crumbs"><a href="#home">Trang chủ</a> › <a href="#jobs">Vị trí thực tập</a> › '+esc(j.title)+'</p><div class="detail-layout"><div class="detail-main">'
    +box('<h1>'+esc(j.title)+'</h1><p class="salary">'+esc(money(j.salary_min,j.salary_max))+'</p>'
      +'<div class="info-trio">'+infoItem(iconPin,!d.address&&d.work_address&&j.work_mode!=='remote'?'Địa điểm làm việc demo':'Địa điểm',d.address||d.work_address||j.location)+infoItem(iconExp,'Kinh nghiệm',d.experience||'—')+infoItem(iconCal,'Hạn ứng tuyển',j.deadline||'Linh hoạt')+'</div>'
      +'<div class="cta-row">'+(canApply?'<button type="button" data-action="goto-apply">Ứng tuyển ngay</button>':!user?'<a class="button" href="#login">Đăng nhập để ứng tuyển</a>':'')
      +(user&&j.active?saveButton(j.id,j.title,ids.has(j.id)):'')+'</div>')
    +box('<h2 class="section-title">Tổng quan</h2>'+overviewRow('Kỹ năng',j.skills?.length?tags(...j.skills):'')+overviewRow('Ngành',tags(j.category))
      +overviewRow('Hình thức',tags(workMode))+overviewRow('Thời gian',d.working_hours?tags(...String(d.working_hours).split('\n').map(x=>x.trim()).filter(Boolean)):''))
    +box('<h2 class="section-title">Mô tả công việc</h2>'+bullets(j.description)+'<h2 class="section-title">Yêu cầu</h2>'+bullets(j.requirements)
      +(d.responsibilities?'<h2 class="section-title">Trách nhiệm</h2>'+bullets(d.responsibilities):'')
      +(d.nice_to_have?'<h2 class="section-title">Ưu tiên</h2>'+copy(d.nice_to_have):'')
      +(d.application_process?'<h2 class="section-title">Quy trình ứng tuyển</h2>'+copy(d.application_process):'')
      +(d.benefits||d.benefit_groups?.length?'<h2 class="section-title">Quyền lợi</h2>'+bullets(d.benefits)+benefitList(d):''))
    +'</div><aside class="detail-side">'
    +box('<div class="company-head">'+logoTile(j.company_id,j.company_name,true,c?.has_logo??j.company_has_logo)+'<h3>'+esc(j.company_name)+'</h3></div>'
      +'<div class="company-facts">'+(cd.company_size?'<p><b>Quy mô:</b> '+esc(cd.company_size)+' nhân viên</p>':'')
      +((cd.address||c?.city)?'<p><b>Địa điểm:</b> '+esc(cd.address||c.city)+'</p>':'')+(c?.industry?'<p><b>Ngành nghề:</b> '+esc(c.industry)+'</p>':'')+'</div>'
      +link('company/'+j.company_id,'Xem trang công ty')).replace('class="panel"','class="panel company-card"')
    +box('<h2 class="section-title">Thông tin chung</h2><dl class="facts">'+fact('Cấp bậc',levelLabel[j.level]||j.level)+fact('Học vấn',d.education)
      +fact('Số lượng tuyển',d.quantity?d.quantity+' người':'')+fact('Hình thức làm việc',workMode)
      +fact('Lịch làm việc',d.working_days||scheduleLabel[d.employment_schedule])+fact('Ca làm',d.shift_details)+'</dl>')
    +(user&&j.active?box('<details><summary>Báo cáo tin tuyển dụng</summary>'+form('job-report',
        area('reason','Lý do báo cáo','','required minlength="10" maxlength="2000"'),'Gửi báo cáo')+'</details>'):'')
    +'</aside></div>';
  if(user&&j.active)bindForm(root,'job-report',async(data,el)=>{
    await api('/jobs/'+j.id+'/reports',{method:'POST',data});
    el.reset();toast('Đã gửi báo cáo cho quản trị viên');
  });
  bindHearts(root,user,ids);
  action(root,'goto-apply',()=>root.querySelector('#apply-section')?.scrollIntoView({behavior:'smooth'}));
  if(canApply){
    const cvs=await api('/students/me/cvs');
    root.querySelector('.detail-main').insertAdjacentHTML('beforeend','<div id="apply-section">'+box('<h2 class="section-title">Ứng tuyển</h2>'+form('apply',select('cv_id','CV',[['','Dùng hồ sơ hiện tại'],...cvs.map(c=>[c.id,c.original_name])])
      +area('cover_letter','Thư ứng tuyển','','maxlength="5000"')
      +'<p class="muted">Khi gửi đơn, doanh nghiệp sẽ xem được họ tên, ngành học, kỹ năng trong CV bạn chọn, thư ứng tuyển và tệp CV đính kèm.</p>','Gửi đơn'))+'</div>');
    bindForm(root,'apply',async values=>{
      await api('/applications',{method:'POST',data:{...values,job_id:j.id,cv_id:Number(values.cv_id)||null}});
      toast('Đã gửi đơn');location.hash='applications';
    });
  }
}
export const companyCard=c=>'<article class="card top-card"><div class="top-card-head">'+logoTile(c.id,c.name,false,c.has_logo)
  +'<div><h3><a href="#company/'+c.id+'">'+esc(c.name)+'</a></h3><p class="muted">'+esc(c.industry)+'</p></div></div>'
  +companyPhoto(c.name)+'<div class="top-card-foot">'+tags(c.city,c.details?.company_size&&c.details.company_size+' nhân viên')+'</div></article>';
const COMPANY_PAGE=12;
async function companies({root,args}){
  const all=await api('/companies');
  const pages=Math.max(1,Math.ceil(all.length/COMPANY_PAGE));
  const current=Math.min(pages,Math.max(1,Number(new URLSearchParams(args[0]||'').get('page'))||1));
  const records=all.slice((current-1)*COMPANY_PAGE,current*COMPANY_PAGE);
  root.innerHTML=heading('Doanh nghiệp','Khám phá hồ sơ các doanh nghiệp đang có trên hệ thống.')
    +'<section class="section" aria-labelledby="demo-companies-title">'
    +'<div class="section-heading"><div><p class="eyebrow">Dữ liệu ứng tuyển mẫu</p>'
    +'<h2 id="demo-companies-title">Doanh nghiệp trên hệ thống</h2></div></div>'
    +(records.length?'<div class="top-grid">'+records.map(companyCard).join('')+'</div>':empty())
    +pager(current,pages,current-1,current+1)+'</section>';
  action(root,'page',n=>{location.hash='companies/'+new URLSearchParams({page:n});});
}
const iconUsers=svg('<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.6a3.5 3.5 0 0 1 0 6.8M18 14.2A6.5 6.5 0 0 1 21.5 20"/>');
const iconBuilding=svg('<path d="M4 21V5a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v16M14 10h5a1 1 0 0 1 1 1v10M2 21h20M8 8h2M8 12h2M8 16h2"/>');
const iconLink=svg('<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>');
const iconShield=svg('<path d="M12 3 4 6v6c0 4.5 3.2 8 8 9 4.8-1 8-4.5 8-9V6z"/><path d="m8.5 12 2.5 2.5 4.5-5"/>');
const small=icon=>icon.replace('width="20" height="20"','width="16" height="16"');
const siteUrl=raw=>{
  const value=String(raw||'').trim();
  if(!value)return null;
  try{
    const url=new URL(/^https?:\/\//i.test(value)?value:'https://'+value);
    return /^https?:$/.test(url.protocol)?{href:url.href,text:url.host+(url.pathname==='/'?'':url.pathname)}:null;
  }catch{return null;}
};
const jobRow=ids=>j=>{
  const workMode=modes.find(([key])=>key===j.work_mode)?.[1];
  return '<article class="job-row">'+logoTile(j.company_id,j.company_name,false,j.company_has_logo)
    +'<div class="job-row-body"><h3><a href="#job/'+j.id+'">'+esc(j.title)+'</a></h3><p class="muted">'+esc(j.company_name)+'</p>'
    +tags(j.location,workMode,levelLabel[j.level]||j.level)+'</div>'
    +'<div class="job-row-side"><b class="job-salary">'+esc(money(j.salary_min,j.salary_max))+'</b>'+heartButton(j.id,j.title,ids.has(j.id))+'</div></article>';
};
const COMPANY_JOBS=10;
async function company({root,args,user,signal}){
  const id=Number(args[0]);
  const [c,all,ids,reviews]=await Promise.all([api('/companies/'+id),api('/jobs?company_id='+id+'&limit=100'),savedIds(user),api('/companies/'+id+'/reviews')]);
  const d=c.details||{}, site=siteUrl(d.website);
  const locations=[...new Set(all.items.map(j=>j.location).filter(Boolean))];
  let following=Boolean(c.following), followers=c.followers||0;
  const followText=()=>following?'✓ Đang theo dõi':'+ Theo dõi';
  const about=[['Sứ mệnh',d.mission],['Tầm nhìn',d.vision],['Giá trị cốt lõi',d.core_values],['Văn hoá',d.culture],['Quyền lợi',d.benefits],['Lịch làm việc',d.work_schedule],['Chính sách làm việc',d.work_policy],['Giờ nghỉ trưa',d.lunch_break],['Quy trình tuyển dụng',d.hiring_process],['Chính sách thực tập',d.internship_policy]].filter(([,value])=>value)
    .map(([title,value])=>'<h3 class="co-sub">'+title+'</h3>'+copy(value)).join('');
  const where=d.address?(c.city&&!d.address.includes(c.city)?d.address+', '+c.city:d.address):c.city;
  const searchForm='<form class="co-search" id="co-search" role="search"><label class="co-q">'+searchIcon
    +'<input type="search" name="q" placeholder="Tên công việc, vị trí ứng tuyển…" maxlength="200" aria-label="Tìm trong tin tuyển dụng"></label>'
    +'<label class="co-loc">'+pinIcon+'<select name="location" aria-label="Tỉnh/thành phố"><option value="">Tất cả tỉnh/thành phố</option>'
    +locations.map(l=>'<option value="'+esc(l)+'">'+esc(l)+'</option>').join('')+'</select></label>'
    +'<button type="submit">'+searchIcon+' Tìm kiếm</button></form>';
  root.innerHTML='<section class="panel co-head"><div class="co-top">'+logoTile(c.id,c.name,true,c.has_logo)
    +'<div class="co-title"><h1>'+esc(c.name)+'</h1><p class="co-meta">'
    +(site?'<a href="'+esc(site.href)+'" target="_blank" rel="noopener noreferrer">'+small(iconLink)+esc(site.text)+'</a>':'')
    +'<span>'+small(iconUsers)+'<span id="co-followers">'+followers.toLocaleString('vi-VN')+'</span> người theo dõi</span></p></div>'
    +'<button type="button" class="follow-btn" data-action="follow" aria-pressed="'+following+'">'+followText()+'</button></div>'
    +'<div class="co-tabs" role="group" aria-label="Mục của công ty"><button type="button" class="co-tab" data-tab="co-about" aria-current="true">Tổng quan</button>'
    +'<button type="button" class="co-tab" data-tab="co-jobs" aria-current="false">Tin tuyển dụng ('+all.total+')</button></div></section>'
    +'<div class="detail-layout"><div class="detail-main">'
    +'<section class="panel" id="co-about"><h2 class="co-section-title">Giới thiệu công ty</h2>'+companyPhoto(c.name,true)+copy(c.description)+about+benefitList(d)+'</section>'
    +(reviews.length?box('<h2>Đánh giá sau thực tập</h2>'+reviews.map(r=>tags(r.student_rating+'/5')+copy(r.student_review)).join('')):'')
    +'<section class="panel" id="co-jobs"><h2 class="co-section-title">Tin tuyển dụng</h2>'
    +(all.total?searchForm+'<div id="co-job-list" aria-live="polite"></div>':empty('Công ty chưa có tin tuyển dụng đang mở.'))+'</section>'
    +'</div><aside class="detail-side">'
    +box('<h2 class="co-section-title">Thông tin chung</h2><div class="co-info">'
      +(d.founded_year?infoItem(iconCal,'Năm thành lập',d.founded_year):'')
      +(d.company_size?infoItem(iconUsers,'Quy mô',d.company_size+' nhân viên'):'')
      +(c.industry?infoItem(iconBuilding,'Ngành nghề',c.industry):'')
      +(d.verification_status==='verified'?infoItem(iconShield,'Xác minh','Đã xác minh'):'')+'</div>')
    +(where?box('<h2 class="co-section-title">Địa điểm công ty</h2><div class="co-info">'+infoItem(iconPin,d.address_is_synthetic?'Địa chỉ văn phòng demo':'Địa chỉ',where)+'</div>'):'')
    +'</aside></div>';

  action(root,'follow',async(_,button)=>{
    if(!user){location.hash='login';return;}
    const next=!following;
    await api('/companies/'+c.id+'/follow?value='+next,{method:'PUT'});
    following=next;
    followers=Math.max(0,followers+(next?1:-1));
    button.textContent=followText();
    button.setAttribute('aria-pressed',String(following));
    root.querySelector('#co-followers').textContent=followers.toLocaleString('vi-VN');
    toast(next?'Đã theo dõi công ty':'Đã bỏ theo dõi công ty');
  });
  const tabs=[...root.querySelectorAll('.co-tab')];
  for(const tab of tabs)tab.addEventListener('click',()=>{
    for(const other of tabs)other.setAttribute('aria-current',String(other===tab));
    root.querySelector('#'+tab.dataset.tab).scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});
  });
  bindHearts(root,user,ids);
  if(!all.total)return;

  const state={q:'',location:'',offset:0}, list=root.querySelector('#co-job-list');
  async function loadJobs(){
    const params=new URLSearchParams({company_id:c.id,limit:COMPANY_JOBS,offset:state.offset});
    if(state.q)params.set('q',state.q);
    if(state.location)params.set('location',state.location);
    list.setAttribute('aria-busy','true');
    try{
      const page=await api('/jobs?'+params,{signal});
      list.innerHTML=(page.items.length?page.items.map(jobRow(ids)).join(''):empty('Không có tin nào khớp với tìm kiếm.'))
        +pager(Math.floor(page.offset/page.limit)+1,Math.ceil(page.total/page.limit),Math.max(0,page.offset-page.limit),page.offset+page.limit);
      action(list,'page',async offset=>{
        state.offset=Number(offset);
        await loadJobs();
        root.querySelector('#co-jobs').scrollIntoView({block:'start'});
      });
    }catch(error){
      if(error.name!=='AbortError')list.innerHTML=empty(error.message);
    }finally{list.removeAttribute('aria-busy');}
  }
  bindForm(root,'co-search',values=>{
    state.q=(values.q||'').trim();
    state.location=values.location||'';
    state.offset=0;
    return loadJobs();
  });
  root.querySelector('#co-search').addEventListener('change',event=>{
    if(event.target.name==='location')event.currentTarget.requestSubmit();
  });
  await loadJobs();
}
async function login({root,user}){
  if(user){root.innerHTML=heading('Bạn đã đăng nhập',user.email)+link('home','Trang chủ');return;}
  root.innerHTML='<div class="auth">'+heading('Đăng nhập','Dùng tài khoản đã kích hoạt trong bộ dữ liệu hoặc đăng ký sinh viên.')
    +box(form('login',field('email','Email','','email','required autocomplete="username"')+field('password','Mật khẩu','','password','required autocomplete="current-password"'),'Đăng nhập'))
    +box('<h2>Tài khoản mẫu</h2><p class="muted">Dùng mật khẩu demo đã đặt khi seed. Mặc định LocalDemo2026!</p><div class="row">'
    +[['usr-demo-s001','Sinh viên'],['usr-demo-c001','Doanh nghiệp'],['staff-demo','Kiểm duyệt'],['admin-demo','Admin']].map(([k,v])=>btn('demo',v,k+'@example.invalid')).join('')
    +'</div>')+link('forgot','Quên mật khẩu?')+link('register','Đăng ký sinh viên')+'</div>';
  action(root,'demo',email=>{root.querySelector('#login [name=email]').value=email;root.querySelector('#login [name=password]').focus();});
  bindForm(root,'login',async data=>{await api('/auth/login',{method:'POST',data});location.hash='home';});
}
async function register({root}){
  root.innerHTML='<div class="auth">'+heading('Đăng ký sinh viên')+box(form('register',field('name','Họ tên','','text','required')+field('email','Email','','email','required')
    +field('password','Mật khẩu','','password','required minlength="8" autocomplete="new-password"'),'Tạo tài khoản'))+'</div>';
  bindForm(root,'register',async data=>{await api('/auth/register',{method:'POST',data});location.hash='profile';});
}
async function forgot({root,user}){
  root.innerHTML='<div class="auth">'+heading('Quên mật khẩu','Nhập email đăng ký trên Internship Connect để yêu cầu liên kết đặt lại mật khẩu.')
    +box(form('forgot',field('email','Email',user?.email,'email','required maxlength="255" autocomplete="username"')
      +'<p role="status" id="forgot-status" hidden></p>','Gửi liên kết'))
    +(user?link('account','Quay lại cài đặt'):link('login','Quay lại đăng nhập'))+'</div>';
  bindForm(root,'forgot',async data=>{
    const status=root.querySelector('#forgot-status');
    status.hidden=true;
    try{
      await api('/auth/forgot-password',{method:'POST',data});
      root.querySelector('#forgot').closest('.panel').innerHTML='<p>Đã tiếp nhận yêu cầu. Nếu email thuộc tài khoản đủ điều kiện, hãy kiểm tra hộp thư đến và thư rác. Liên kết có hiệu lực trong 1 giờ và dùng được một lần.</p>';
    }catch(error){
      status.textContent=error.message;
      status.hidden=false;
    }
  });
}
async function reset({root,args}){
  const token=args[0];
  if(!token){root.innerHTML='<div class="auth">'+heading('Liên kết không hợp lệ','Hãy yêu cầu đặt lại mật khẩu để nhận liên kết mới.')+link('forgot','Quên mật khẩu')+'</div>';return;}
  root.innerHTML='<div class="auth">'+heading('Đặt mật khẩu mới')+box(form('reset',field('password','Mật khẩu mới','','password','required minlength="8" maxlength="128" autocomplete="new-password"')
    +field('confirm','Nhập lại mật khẩu mới','','password','required minlength="8" maxlength="128" autocomplete="new-password"'),'Đặt mật khẩu'))+'</div>';
  bindForm(root,'reset',async data=>{
    if(data.password!==data.confirm)throw new Error('Hai mật khẩu không khớp.');
    await api('/auth/reset-password',{method:'POST',data:{token,password:data.password}});
    toast('Đã đặt lại mật khẩu. Hãy đăng nhập bằng mật khẩu mới.');location.hash='login';
  });
}
export const pages={home,jobs,job,companies,company,login,register,forgot,reset};
