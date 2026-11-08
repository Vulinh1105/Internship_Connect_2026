import {api} from './api/client.js';
import {esc,heading,empty,toast,action,btn} from './components/ui.js';
import * as publicPages from './pages/public.js';
import * as student from './pages/student.js?v=cv-pdf-2';
import * as workspace from './pages/workspace.js?v=chat-history-1';
import * as ai from './pages/ai.js?v=chat-history-1';

const root=document.querySelector('#page'), nav=document.querySelector('#nav');
const routes={...publicPages.pages,...student.pages,...workspace.pages,...ai.pages};
let user=null, last=0;
const common=[['jobs','Thực tập'],['companies','Doanh nghiệp']];
const studentNav=[['profile','Hồ sơ CV'],['matching','AI Matching'],['applications','Đơn ứng tuyển'],['mock','Phỏng vấn ảo']];
const roleNav={student:studentNav,company_member:[['workspace','Quản lý tuyển dụng']],staff:[['moderation','Kiểm duyệt']],admin:[['moderation','Kiểm duyệt'],['accounts','Tài khoản'],['knowledge','Tri thức']]};

async function load(){
  const version=++last;
  const [key='home',...args]=(location.hash.slice(1)||'home').split('/');
  let actor;
  try{actor=await api('/auth/me');}
  catch(error){if(version===last) root.innerHTML=heading('Không kết nối được')+empty(error.message);return;}
  if(version!==last)return;
  user=actor;
  const entries=[...common,...(roleNav[user?.role]||[]),...(user?[['chat','Chatbot'],['notifications','Thông báo']]:[['login','Đăng nhập']])];
  nav.innerHTML=entries.map(([path,text])=>'<a href="#'+path+'"'+(key===path?' aria-current="page"':'')+'>'+esc(text)+'</a>').join('')
    +(user?btn('logout','Thoát'):'');
  action(nav,'logout',async()=>{await api('/auth/logout',{method:'POST'});location.hash='home';await load();});
  const stage=document.createElement('div');
  root.innerHTML=empty('Đang tải…');
  try{
    await (routes[key]||publicPages.pages.home)({root:stage,user,args,reload:load});
  }catch(error){
    stage.innerHTML=heading('Không mở được trang')+empty(error.message);
  }
  if(version===last)root.replaceChildren(stage);
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
