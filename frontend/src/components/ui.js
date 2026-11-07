export const esc = value => String(value ?? '').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const tags = (...values) => '<div class="meta">'+values.filter(Boolean).map(v=>'<span class="tag">'+esc(v)+'</span>').join('')+'</div>';
export const box = html => '<section class="panel">'+html+'</section>';
export const copy = text => '<p class="body-copy">'+esc(text)+'</p>';
export const empty = (message='Chưa có dữ liệu.')=>'<p class="empty">'+esc(message)+'</p>';
export const heading = (title,desc='')=>'<h1>'+esc(title)+'</h1><p class="muted">'+esc(desc)+'</p>';
export const field = (name,label,value='',type='text',attrs='')=>'<label class="field">'+esc(label)+'<input name="'+name+'" type="'+type+'" value="'+esc(value)+'" '+attrs+'></label>';
export const area = (name,label,value='',attrs='')=>'<label class="field">'+esc(label)+'<textarea name="'+name+'" '+attrs+'>'+esc(value)+'</textarea></label>';
export const select = (name,label,items,chosen='')=>'<label class="field">'+esc(label)+'<select name="'+name+'">'+items.map(i=>{
  const [value,text]=Array.isArray(i)?i:[i,i];
  return '<option value="'+esc(value)+'" '+(String(value)===String(chosen)?'selected':'')+'>'+esc(text)+'</option>';
}).join('')+'</select></label>';
export const link = (href,text)=>'<a class="button secondary" href="#'+esc(href)+'">'+esc(text)+'</a>';
export const btn = (action,label,value='')=>'<button type="button" class="secondary" data-action="'+esc(action)+'" data-value="'+esc(value)+'">'+esc(label)+'</button>';
export const form = (id,html,label)=>'<form class="stack" id="'+id+'">'+html+'<div><button>'+esc(label)+'</button></div></form>';
export const grid = items => items.length?'<div class="grid">'+items.join('')+'</div>':empty();
export const money = (min,max)=>min==null&&max==null?'Thoả thuận':[min,max].filter(x=>x!=null).map(x=>Number(x).toLocaleString('vi-VN')).join(' – ')+' ₫';
export const status = code=>({pending:'Chờ xử lý',reviewing:'Đang xét',accepted:'Đã nhận',rejected:'Từ chối',withdrawn:'Đã rút',open:'Đang mở',closed:'Đã đóng',approved:'Đã duyệt',draft:'Bản nháp',invited:'Đã mời',confirmed:'Đã xác nhận',declined:'Đã từ chối',reschedule_requested:'Xin đổi lịch',cancelled:'Đã hủy',active:'Đang luyện',expired:'Hết hạn',abandoned:'Đã dừng',finished:'Hoàn thành',published:'Công khai',archived:'Đã lưu trữ'}[code]||code);
export const modes=[['onsite','Tại văn phòng'],['hybrid','Kết hợp'],['remote','Từ xa']];
export const list = str=>String(str||'').split(/[,\n]/).map(v=>v.trim()).filter(Boolean);
let toastTimer;
export function toast(message){
  document.querySelector('#notice').textContent=message;
  clearTimeout(toastTimer);
  toastTimer=setTimeout(()=>document.querySelector('#notice').textContent='',4500);
}
export function bindForm(root,id,handler,{keepFiles=false}={}){
  root.querySelector('#'+id)?.addEventListener('submit',async e=>{
    e.preventDefault();
    const form=e.currentTarget, button=e.submitter;
    if(button)button.disabled=true;
    try{
      const data=new FormData(form);
      await handler(keepFiles?data:Object.fromEntries(data),form);
    }catch(error){toast(error.message);}
    finally{if(button)button.disabled=false;}
  });
}
export function action(root,name,handler){
  for(const element of root.querySelectorAll('[data-action="'+name+'"]')){
    element.addEventListener('click',async()=>{
      element.disabled=true;
      try{await handler(element.dataset.value,element);}
      catch(error){toast(error.message);}
      finally{element.disabled=false;}
    });
  }
}
