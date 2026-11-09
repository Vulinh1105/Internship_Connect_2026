import {api} from '../api/client.js';
import {action, bindForm, box, btn, copy, empty, esc, field, form, heading, select, toast} from '../components/ui.js';
import {loginRequired} from './public.js';

const noticeOptions=[['applications','Đơn ứng tuyển'],['interviews','Lịch phỏng vấn'],['jobs','Tin tuyển dụng'],['system','Hệ thống']];
const profileOptions=[['major','Ngành học'],['skills','Kỹ năng'],['school','Trường'],['specialization','Chuyên ngành'],['study_year','Năm học'],['summary','Giới thiệu']];
const checks=(items,chosen)=>items.map(([key,label])=>'<label><input type="checkbox" name="'+key+'" value="1" '+(chosen.includes(key)?'checked':'')+'> '+esc(label)+'</label>').join(' ');
const picked=(items,data)=>items.filter(([key])=>data[key]).map(([key])=>key);
const password=(key,label)=>field(key,label,'','password','required maxlength="128" autocomplete="current-password"');

async function account({root,user,reload}){
  if(!user)return loginRequired(root);
  const [settings,sessions]=await Promise.all([api('/auth/settings'),api('/auth/sessions')]);
  const profile=user.role==='student';
  root.innerHTML=heading('Tài khoản & cài đặt',user.email)
    +box('<h2>Thông tin tài khoản</h2>'
      +(settings.has_avatar?'<img width="72" height="72" src="/api/auth/settings/avatar" alt="Ảnh đại diện"> '+btn('remove-avatar','Xóa ảnh'):'')
      +form('avatar','<label class="field">Ảnh đại diện (tối đa 2 MB)<input required type="file" name="file" accept=".png,.jpg,.jpeg,.webp"></label>',settings.has_avatar?'Thay ảnh':'Tải ảnh lên')
      +form('settings','<div class="form-grid">'+field('name','Họ tên',settings.name)+field('region','Khu vực',settings.region)+field('phone','Điện thoại',settings.phone,'tel')+'</div>'
        +'<fieldset><legend>Thông báo trên web</legend>'+checks(noticeOptions,settings.notification_groups||noticeOptions.map(([key])=>key))+'</fieldset>'
        +(settings.email_available?'<fieldset><legend>Thông báo qua email</legend>'
          +checks(noticeOptions.map(([key,label])=>['email_'+key,label]),(settings.email_groups||[]).map(key=>'email_'+key))+'</fieldset>':'')
        +(profile?'<fieldset><legend>Việc làm phù hợp</legend>'+checks([['job_alerts','Báo khi có tin mới phù hợp với nguyện vọng']],settings.job_alerts?['job_alerts']:[])+'</fieldset>':'')
        +(profile?'<fieldset><legend>Thông tin hồ sơ hiển thị trong đơn ứng tuyển</legend>'+checks(profileOptions,settings.profile_fields||['major','skills'])+'</fieldset>':''),
        'Lưu cài đặt')
      +(settings.email_available?form('email',field('email','Email mới','','email','required maxlength="255"')+password('password','Mật khẩu hiện tại'),'Gửi liên kết xác minh')
        :copy('Đổi email qua liên kết xác minh khả dụng khi hệ thống cấu hình gửi email.')))
    +box('<h2>Đổi mật khẩu</h2>'+form('password',password('current_password','Mật khẩu hiện tại')
      +field('new_password','Mật khẩu mới','','password','required minlength="8" maxlength="128" autocomplete="new-password"')
      +field('confirm','Nhập lại mật khẩu mới','','password','required minlength="8" maxlength="128" autocomplete="new-password"'),'Đổi mật khẩu'))
    +box('<h2>Phiên đăng nhập</h2>'+(sessions.length?sessions.map(s=>'<div class="row">'+esc(s.device||'Thiết bị chưa xác định')+' · '+esc(s.created_at.replace('T',' '))
      +(s.current?' · Phiên hiện tại ':' ')+btn('revoke',s.current?'Đăng xuất':'Thu hồi',s.id)+'</div>').join(''):empty('Chưa có phiên được ghi nhận.'))
      +btn('logout-others','Đăng xuất các thiết bị khác'))
    +box('<h2>Quyền riêng tư</h2><details><summary>Chính sách quyền riêng tư</summary>'
      +copy('Hệ thống lưu thông tin tài khoản, hồ sơ ứng tuyển và lịch sử luyện tập để cung cấp chức năng tương ứng. Doanh nghiệp xem CV và thông tin bạn chia sẻ trong đơn gửi tới họ. Bạn có thể yêu cầu quản trị viên vô hiệu hóa hoặc xóa tài khoản.')+'</details>'
      +'<details><summary>Điều khoản sử dụng</summary>'+copy('Cung cấp thông tin chính xác, tôn trọng quyền riêng tư và chỉ sử dụng hồ sơ ứng tuyển cho mục đích tuyển dụng.')+'</details>'
      +(settings.closure_request?copy('Yêu cầu của bạn đang chờ quản trị viên xử lý.'):'')
      +form('closure',select('action','Yêu cầu tài khoản',[['disable','Vô hiệu hóa'],['delete','Xóa tài khoản']])
        +password('password','Nhập mật khẩu để xác nhận'),'Gửi yêu cầu'));

  bindForm(root,'settings',async data=>{
    const {name,region,phone}=data;
    await api('/auth/settings',{method:'PUT',data:{name,region,phone,notification_groups:picked(noticeOptions,data),
      email_groups:settings.email_available?noticeOptions.filter(([key])=>data['email_'+key]).map(([key])=>key):settings.email_groups||[],
      job_alerts:profile&&Boolean(data.job_alerts),profile_fields:profile?picked(profileOptions,data):settings.profile_fields||[]}});
    toast('Đã lưu cài đặt');await reload();
  });
  bindForm(root,'avatar',async data=>{await api('/auth/settings/avatar',{method:'POST',data});await reload();},{keepFiles:true});
  action(root,'remove-avatar',async()=>{await api('/auth/settings/avatar',{method:'DELETE'});await reload();});
  if(settings.email_available)bindForm(root,'email',async(data,el)=>{
    await api('/auth/settings/email',{method:'POST',data});el.reset();toast('Hãy kiểm tra email mới.');
  });
  bindForm(root,'password',async (data,el)=>{
    if(data.new_password!==data.confirm)throw new Error('Hai mật khẩu mới không khớp.');
    await api('/auth/change-password',{method:'POST',data:{current_password:data.current_password,new_password:data.new_password}});
    el.reset();toast('Đã đổi mật khẩu và đăng xuất các thiết bị khác');await reload();
  });
  action(root,'revoke',async id=>{await api('/auth/sessions/'+encodeURIComponent(id),{method:'DELETE'});await reload();});
  action(root,'logout-others',async()=>{await api('/auth/logout-others',{method:'POST'});await reload();});
  bindForm(root,'closure',async data=>{
    if(!confirm('Gửi yêu cầu này cho quản trị viên?'))return;
    await api('/auth/settings/closure',{method:'POST',data});await reload();
  });
}
async function confirmEmail({root,user,args,reload}){
  if(!user){
    root.innerHTML=heading('Xác minh email')+copy('Đăng nhập rồi mở lại liên kết trong email.');
    return;
  }
  root.innerHTML=heading('Xác minh email mới')+btn('confirm-email','Xác minh');
  action(root,'confirm-email',async()=>{
    await api('/auth/settings/email/confirm',{method:'POST',data:{token:args[0]||''}});
    toast('Đã xác minh email mới');location.hash='account';
  });
}

export const pages={account,'confirm-email':confirmEmail};
