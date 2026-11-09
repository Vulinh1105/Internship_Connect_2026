import {api} from './api/client.js';
import {esc,heading,empty,toast,action,btn} from './components/ui.js';
import {watchSelects} from './components/dropdown.js';
import * as publicPages from './pages/public.js?v=blue-2';
import * as student from './pages/student.js?v=merge-fix-3';
import * as notices from './pages/notifications.js?v=notice-2';
import * as workspace from './pages/workspace.js?v=workspace-dash-3';
import * as ai from './pages/ai.js?v=interview-avatar-2';

const root=document.querySelector('#page'), nav=document.querySelector('#nav');
watchSelects(root);
const routes={...publicPages.pages,...student.pages,...notices.pages,...workspace.pages,...ai.pages};
let user=null, last=0, activePage, badgeTimer;
const badgeFor=path=>path==='notifications'||(path==='moderation'&&['staff','admin'].includes(user?.role))?badge(path):'';
const common=[['jobs','Thực tập'],['companies','Doanh nghiệp']];
const studentNav=[['profile','Hồ sơ CV'],['matching','AI Matching'],['applications','Đơn ứng tuyển'],['mock','Phỏng vấn ảo']];
const roleNav={student:studentNav,company_member:[['workspace','Quản lý tuyển dụng']],staff:[['moderation','Kiểm duyệt']],admin:[['moderation','Kiểm duyệt'],['accounts','Tài khoản'],['knowledge','Tri thức']]};

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
  const entries=[...common,...(roleNav[user?.role]||[]),...(user?[['chat','Chatbot'],['notifications','Thông báo'],['account','Đổi mật khẩu']]:[['login','Đăng nhập']])];
  nav.innerHTML=entries.map(([path,text])=>'<a href="#'+path+'"'+(key===path?' aria-current="page"':'')+'>'+esc(text)+(badgeFor(path))+'</a>').join('')
    +(user?btn('logout','Thoát'):'');
  paintBadges(nav);
  action(nav,'logout',async()=>{await api('/auth/logout',{method:'POST'});location.hash='home';await load();});
  const stage=document.createElement('div');
  root.innerHTML=empty('Đang tải…');
  try{
    await (routes[key]||publicPages.pages.home)({root:stage,user,args,reload:load,signal:page.signal});
  }catch(error){
    stage.innerHTML=heading('Không mở được trang')+empty(error.message);
  }
  if(version!==last)return;
  const adminKeys=['moderation','accounts','knowledge'];
  if(['staff','admin'].includes(user?.role)&&adminKeys.includes(key)){
    const layout=document.createElement('div');
    layout.className='admin-layout';
    layout.innerHTML='<aside class="admin-side" aria-label="Quản trị">'+roleNav[user.role].map(([path,text])=>'<a href="#'+path+'"'+(key===path?' aria-current="page"':'')+'>'+esc(text)+badgeFor(path)+'</a>').join('')+'</aside>';
    stage.classList.add('admin-content');
    layout.append(stage);
    root.replaceChildren(layout);
    paintBadges(layout);
  }else root.replaceChildren(stage);
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
