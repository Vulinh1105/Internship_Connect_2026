import {api} from '../api/client.js';
import {esc,heading,empty,btn,action} from '../components/ui.js';
import {loginRequired} from './public.js';

const svg=path=>'<svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'+path+'</svg>';
const icons={
  calendar:svg('<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M8 3v4M16 3v4M4 10h16"/>'),
  application:svg('<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5M10 13h6M10 17h6"/>'),
  job:svg('<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2M3 13h18"/>')
};
const kinds={
  interview:['calendar','applications'],interview_invited:['calendar','applications'],
  interview_cancelled:['calendar','applications'],interview_reply:['calendar','workspace'],
  application_status:['application','applications'],application_new:['application','applicants'],
  application_withdrawn:['application','applicants'],company_new_job:['job','job'],job_approved:['job','workspace'],job_rejected:['job','workspace']
};
// Trang đích theo loại thông báo; target_id là mã tin khi trang đích cần (hồ sơ ứng tuyển, chi tiết tin).
export function destination(n){
  const [,page='notifications']=kinds[n.kind]||[];
  if(page==='applicants')return n.target_id!=null?'applicants/'+n.target_id:'workspace';
  return page==='job'&&n.target_id!=null?'job/'+n.target_id:page==='job'?'jobs':page;
}
const iconOf=n=>icons[(kinds[n.kind]||['application'])[0]];

// created_at do máy chủ lưu theo giờ Việt Nam không kèm múi giờ; người dùng ở Việt Nam đọc như giờ máy.
export function ago(iso){
  const minutes=Math.floor((Date.now()-new Date(iso).getTime())/60000);
  if(minutes<1)return 'Vừa xong';
  if(minutes<60)return minutes+' phút trước';
  if(minutes<1440)return Math.floor(minutes/60)+' giờ trước';
  if(minutes<10080)return Math.floor(minutes/1440)+' ngày trước';
  return new Date(iso).toLocaleDateString('vi-VN');
}
const isToday=iso=>new Date(iso).toDateString()===new Date().toDateString();

const row=n=>'<li><a class="notice-item'+(n.read_at?'':' unread')+'" href="#'+esc(destination(n))+'" data-notice="'+n.id+'">'
  +'<span class="notice-icon">'+iconOf(n)+'</span><span class="notice-body"><span class="notice-text">'+esc(n.message)+'</span>'
  +'<small class="muted">'+esc(ago(n.created_at))+'</small></span>'
  +(n.read_at?'':'<span class="notice-dot" role="img" aria-label="Chưa đọc"></span>')+'</a></li>';
const group=(title,items)=>items.length?'<h2 class="notice-group">'+title+'</h2><ul class="notice-list">'+items.map(row).join('')+'</ul>':'';

async function notifications({root,user,reload}){
  if(!user)return loginRequired(root);
  const rows=await api('/notifications');
  const unread=rows.filter(n=>!n.read_at).length;
  root.innerHTML=heading('Thông báo',unread?'Bạn có '+unread+' thông báo chưa đọc.':'Bạn đã đọc hết thông báo.')
    +(unread?'<div class="row">'+btn('read-all','Đánh dấu tất cả đã đọc')+'</div>':'')
    +(rows.length?group('Hôm nay',rows.filter(n=>isToday(n.created_at)))+group('Trước đó',rows.filter(n=>!isToday(n.created_at))):empty('Chưa có thông báo.'));
  action(root,'read-all',async()=>{await api('/notifications/read',{method:'POST'});await reload();});
  for(const link of root.querySelectorAll('[data-notice]'))link.addEventListener('click',async event=>{
    event.preventDefault();
    const target=link.getAttribute('href');
    try{await api('/notifications/'+link.dataset.notice+'/read',{method:'POST'});}catch{/* vẫn chuyển trang */}
    if(location.hash===target)await reload();else location.hash=target;
  });
}
export const pages={notifications};
