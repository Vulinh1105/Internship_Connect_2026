import {api} from './api/client.js';
import {esc,heading,empty,toast,action,btn} from './components/ui.js';
import {watchSelects} from './components/dropdown.js';
import * as publicPages from './pages/public.js?v=company-registration-1';
import * as student from './pages/student.js?v=hybrid-match-1';
import * as notices from './pages/notifications.js?v=company-registration-1';
import * as workspace from './pages/workspace.js?v=company-registration-1';
import * as account from './pages/account.js?v=password-reset-1';
import * as registration from './pages/company-registration.js?v=company-registration-test-1';
import * as recruitment from './pages/recruitment.js?v=members-no-invite-1';
import * as ai from './pages/ai.js?v=chat-sidebar-1';

const root=document.querySelector('#page'), nav=document.querySelector('#nav');
const tools=document.querySelector('#header-tools'), toggle=document.querySelector('#nav-toggle');
const header=document.querySelector('.site-header'), launcher=document.querySelector('#chat-launcher');
watchSelects(root);
const routes={...publicPages.pages,...student.pages,...notices.pages,...workspace.pages,...ai.pages,...account.pages,...recruitment.pages,...registration.pages};
let user=null, last=0, activePage;
const common=[['jobs','Thực tập'],['companies','Doanh nghiệp']];
const personal=[['applications','Đơn ứng tuyển'],['saved','Tin đã lưu'],['followed','Đang theo dõi']];
const studentNav=[['matching','AI Matching'],['mock','Phỏng vấn ảo']];
const adminNav={
  staff:[['moderation','Kiểm duyệt']],
  admin:[['company-verification','Kiểm duyệt'],['moderation','Duyệt tin tuyển dụng'],['accounts','Tài khoản'],['knowledge','Tri thức']],
};
const adminPages=new Set(adminNav.admin.map(([path])=>path));
const companyPages=new Set(['workspace','edit','applicants','recruitment-stats','company-members','question-sets']);
const aliases={job:'jobs',company:'companies','mock-session':'mock','confirm-email':'account'};
const bell='<svg aria-hidden="true" width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></svg>';

function routeLink(path,label,key,classes='',group=false){
  return '<a href="#'+path+'"'+(classes?' class="'+classes+'"':'')+(path===key?' aria-current="page"':'')
    +(group?' data-current':'')+'>'+label+'</a>';
}

function setDrawer(open){
  toggle.setAttribute('aria-expanded',String(open));
  toggle.setAttribute('aria-label',open?'Đóng điều hướng':'Mở điều hướng');
  nav.toggleAttribute('data-open',open);
}
function closeMenus(except=null){
  for(const menu of header.querySelectorAll('details[open]')){
    if(menu!==except)menu.open=false;
  }
}
toggle.addEventListener('click',()=>{
  closeMenus();
  setDrawer(toggle.getAttribute('aria-expanded')!=='true');
});
header.addEventListener('click',event=>{
  const summary=event.target.closest('summary');
  if(summary){
    closeMenus(summary.parentElement);
    if(summary.closest('#header-tools'))setDrawer(false);
  }
  if(event.target.closest('a[href^="#"]')){
    closeMenus();
    setDrawer(false);
  }
});
document.addEventListener('click',event=>{
  if(!header.contains(event.target)){
    closeMenus();
    setDrawer(false);
  }
});
document.addEventListener('keydown',event=>{
  if(event.key!=='Escape')return;
  const opened=header.querySelector('details[open]');
  if(opened){
    opened.open=false;
    opened.querySelector('summary').focus();
  }else if(toggle.getAttribute('aria-expanded')==='true'){
    setDrawer(false);
    toggle.focus();
  }
});
matchMedia('(max-width: 880px)').addEventListener('change',()=>{closeMenus();setDrawer(false);});

function renderHeader(key){
  const current=aliases[key]||key;
  const role=user?.role;
  const administration=adminNav[role];
  const links=entries=>entries.map(([path,title])=>routeLink(path,esc(title),current)).join('');
  let prefix='';
  if(administration)prefix=routeLink(administration[0][0],'Quản trị',current,'',adminPages.has(current));
  if(role==='company_member')prefix=routeLink('workspace','Quản lý tuyển dụng',current,'',companyPages.has(current));
  nav.innerHTML=prefix+links(common)+(role==='student'?links(studentNav)
    +'<details class="nav-group"><summary'+(personal.some(([path])=>path===key)?' data-current':'')+'>Việc của tôi <span aria-hidden="true">▾</span></summary>'
    +'<div class="header-menu">'+links(personal)+'</div></details>':'');
  tools.innerHTML=user
    ?'<a class="header-icon" href="#notifications" aria-label="Thông báo" title="Thông báo"'
      +(key==='notifications'?' aria-current="page"':'')+'>'+bell+badge('notifications')+'</a>'
      +'<details class="account-menu"><summary aria-label="Tài khoản" title="Tài khoản">'
      +(user.has_avatar?'<img src="/api/auth/settings/avatar" width="40" height="40" alt="">':esc(user.email.slice(0,1).toUpperCase()))
      +'</summary><div class="header-menu">'
      +(role==='student'?routeLink('profile','Hồ sơ &amp; CV',current):'')
      +routeLink('account','Tài khoản &amp; cài đặt',current)+btn('logout','Thoát')+'</div></details>'
    :routeLink('login','Đăng nhập',key,'header-auth login-link')+routeLink('register','Đăng ký',key,'header-auth register-link')
      +routeLink('register-company','Đăng ký doanh nghiệp',key,'header-auth company-register-link');
  launcher.hidden=!user||key==='chat';
  setDrawer(false);
  paintBadges(tools);
  action(tools,'logout',async()=>{
    await api('/auth/logout',{method:'POST'});
    if(location.hash==='#home')await load();else location.hash='home';
  });
}

const counts={notifications:0,moderation:0};
const badgeLabel={notifications:' thông báo chưa đọc',moderation:' tin đang chờ duyệt'};
function paintBadges(scope=document){
  for(const badge of scope.querySelectorAll('[data-badge]')){
    const key=badge.dataset.badge, count=counts[key]||0;
    badge.hidden=!count;
    badge.textContent=count>99?'99+':String(count||'');
    badge.setAttribute('aria-label',count+badgeLabel[key]);
  }
}
const badge=key=>'<span class="badge" data-badge="'+key+'" hidden></span>';
async function fetchCounts(){
  const staff=['staff','admin'].includes(user?.role);
  const [unread,pending]=await Promise.all([
    api('/notifications/unread-count').then(r=>r.unread)
      .catch(()=>api('/notifications').then(rows=>rows.filter(n=>!n.read_at).length)).catch(()=>0),
    staff?api('/jobs/moderation/count').then(r=>r.pending)
      .catch(()=>api('/jobs/moderation').then(rows=>rows.length)).catch(()=>0):0
  ]);
  counts.notifications=unread;counts.moderation=pending;
}
async function refreshBadge(){
  if(!user||document.hidden)return;
  await fetchCounts();
  paintBadges();
}
setInterval(refreshBadge,60000);
document.addEventListener('visibilitychange',refreshBadge);

async function load(){
  const version=++last;
  activePage?.abort();
  const page=activePage=new AbortController();
  const [key='home',...args]=(location.hash.slice(1)||'home').split('/');
  let actor;
  try{actor=await api('/auth/me');}
  catch(error){if(version===last) root.innerHTML=heading('Không kết nối được')+empty(error.message);return;}
  if(version!==last)return;
  user=actor;
  if(user)await fetchCounts();else counts.notifications=counts.moderation=0;
  if(version!==last)return;
  renderHeader(key);
  const stage=document.createElement('div');
  root.innerHTML=empty('Đang tải…');
  try{
    await (routes[key]||publicPages.pages.home)({root:stage,user,args,reload:load,signal:page.signal});
  }catch(error){
    stage.innerHTML=heading('Không mở được trang')+empty(error.message);
  }
  if(version!==last)return;
  if(adminNav[user?.role]&&adminPages.has(key)){
    const layout=document.createElement('div');
    layout.className='admin-layout';
    layout.innerHTML='<aside class="admin-side" aria-label="Quản trị">'+adminNav[user.role].map(([path,text])=>routeLink(path,esc(text)+(path==='moderation'?badge(path):''),key)).join('')+'</aside>';
    stage.classList.add('admin-content');
    layout.append(stage);
    root.replaceChildren(layout);
    paintBadges(layout);
  }else{
    if(user?.role==='student'&&personal.some(([path])=>path===key)){
      stage.insertAdjacentHTML('afterbegin','<nav class="co-tabs personal-tabs" aria-label="Việc của tôi">'
        +personal.map(([path,title])=>routeLink(path,esc(title),key,'co-tab')).join('')+'</nav>');
    }
    root.replaceChildren(stage);
  }
}
document.querySelector('.skip-link').addEventListener('click',event=>{
  event.preventDefault();
  root.focus();
});
window.addEventListener('hashchange',()=>{
  window.scrollTo(0,0);
  load();
});
load().catch(error=>toast(error.message));
