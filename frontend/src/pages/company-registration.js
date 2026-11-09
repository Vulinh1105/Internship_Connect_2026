import {api} from '../api/client.js';
import {area,bindForm,box,copy,empty,esc,field,form,heading,link,select,toast} from '../components/ui.js';
import {loginRequired} from './public.js';

const endpoint='/company-registrations';
const companyFields=[
  ['name','Tên doanh nghiệp',180],['tax_code','Mã số thuế',14],['registration_number','Số giấy chứng nhận đăng ký doanh nghiệp',80],
  ['industry','Lĩnh vực hoạt động',100],['company_size','Quy mô nhân sự',40],['address','Địa chỉ trụ sở',350],
  ['city','Tỉnh/thành phố',100],['website','Website công ty',250,'url',false],
  ['company_email','Email doanh nghiệp',255,'email'],['company_phone','Số điện thoại công ty',25,'tel'],
];
const contactFields=[
  ['contact_name','Họ và tên',150],['position','Chức vụ',120],
  ['email','Email đăng nhập',255,'email'],['phone','Số điện thoại người đăng ký',25,'tel'],
];
const fields=rows=>rows.map(([name,label,max,type='text',required=true])=>
  field(name,label,'',type,(required?'required ':'')+'maxlength="'+max+'"')).join('');
const documents={
  certificate:'Giấy chứng nhận đăng ký doanh nghiệp',
  authorization:'Giấy ủy quyền',
  identity:'CCCD người đại diện pháp luật',
  logo:'Logo công ty',
};
const file=(name,accept,required=false)=>'<label class="field">'+documents[name]
  +'<input type="file" name="'+name+'" accept="'+accept+'" '+(required?'required':'')+'></label>';
const proofTypes='.pdf,.png,.jpg,.jpeg,.webp';

async function registerCompany({root}){
  root.innerHTML='<div class="company-registration">'+heading('Đăng ký doanh nghiệp',
    'Hồ sơ sẽ được admin xác minh trước khi bạn có thể đăng nhập và đăng tin tuyển dụng.')
    +box(form('register-company','<fieldset class="stack"><legend>Thông tin doanh nghiệp</legend><div class="registration-fields">'
      +fields(companyFields)+file('logo','.png,.jpg,.jpeg,.webp')+'</div></fieldset>'
      +'<fieldset class="stack"><legend>Thông tin người đăng ký</legend><div class="registration-fields">'
      +fields(contactFields)+field('password','Mật khẩu','','password','required minlength="10" maxlength="128" autocomplete="new-password"')
      +select('representative','Bạn là người đại diện theo pháp luật?',[['','Chọn câu trả lời'],['yes','Có'],['no','Không']])
      +'</div><label class="check" data-authorization hidden><input type="checkbox" name="authorized"> Tôi có quyền tuyển dụng thay mặt doanh nghiệp.</label></fieldset>'
      +'<fieldset class="stack"><legend>Giấy tờ xác minh</legend>'+file('certificate',proofTypes,true)
      +'<div data-authorization hidden>'+file('authorization',proofTypes)+'</div>'+file('identity',proofTypes)
      +'<p class="muted">Mỗi giấy tờ tối đa 5 MB. Logo tối đa 2 MB. CCCD chỉ cần khi admin yêu cầu bổ sung.</p></fieldset>',
    'Gửi hồ sơ đăng ký'))+'</div>';
  const registration=root.querySelector('#register-company');
  const representative=registration.elements.namedItem('representative');
  representative.required=true;
  representative.addEventListener('change',()=>{
    const required=representative.value==='no';
    for(const el of registration.querySelectorAll('[data-authorization]'))el.hidden=!required;
    registration.elements.namedItem('authorized').required=required;
    registration.elements.namedItem('authorization').required=required;
  });
  bindForm(root,'register-company',async data=>{
    const payload=Object.fromEntries(data);
    const files=new FormData();
    for(const name of Object.keys(documents)){
      const upload=data.get(name);
      if(upload?.name)files.append(name,upload);
      delete payload[name];
    }
    payload.representative=payload.representative==='yes';
    payload.authorized=payload.authorized==='on';
    files.append('payload',JSON.stringify(payload));
    await api(endpoint,{method:'POST',data:files});
    root.innerHTML=heading('Hồ sơ đang chờ xác minh',
      'Admin đã nhận thông báo. Bạn có thể đăng nhập lại để kiểm tra trạng thái hồ sơ.')
      +link('login','Về trang đăng nhập');
  },{keepFiles:true});
}

async function companyVerification({root,user,args,reload}){
  if(!user)return loginRequired(root);
  const rows=await api(endpoint);
  const labels=[...companyFields,...contactFields].map(([name,label])=>[name,label]);
  root.innerHTML=heading('Thông tin cần kiểm duyệt','Hồ sơ đăng ký tài khoản doanh nghiệp đang chờ xác minh.')
    +(rows.length?rows.map(row=>box('<details'+(String(row.id)===args[0]?' open':'')+'><summary>'
      +esc(row.info.name)+' · '+esc(row.tax_code)+'</summary><dl class="registration-fields">'
      +labels.map(([name,label])=>'<div><dt>'+esc(label)+'</dt><dd>'+esc(name==='tax_code'?row.tax_code:name==='email'?row.email:row.info[name]||'—')+'</dd></div>').join('')
      +'<div><dt>Đại diện theo pháp luật</dt><dd>'+(row.info.representative?'Có':'Không')+'</dd></div>'
      +'<div><dt>Đã xác nhận quyền tuyển dụng</dt><dd>'+(row.info.representative?'Theo tư cách đại diện':row.info.authorized?'Có':'Không')+'</dd></div>'
      +'</dl><div class="row">'+row.documents.map(name=>'<a class="button secondary" href="/api/company-registrations/'+row.id+'/documents/'
        +esc(name)+'">'+esc(documents[name])+'</a>').join('')+'</div>'
      +form('company-review-'+row.id,select('status','Quyết định',[['approved','Duyệt và kích hoạt'],['needs_changes','Yêu cầu bổ sung'],['rejected','Từ chối']])
        +area('reason','Lý do (bắt buộc khi yêu cầu bổ sung hoặc từ chối)','','maxlength="2000"'),'Lưu quyết định')+'</details>')).join('')
      :empty('Chưa có hồ sơ doanh nghiệp cần kiểm duyệt.'));
  for(const row of rows)bindForm(root,'company-review-'+row.id,async data=>{
    if(data.status!=='approved'&&!data.reason.trim())throw new Error('Hãy nhập lý do xử lý hồ sơ.');
    await api(endpoint+'/'+row.id,{method:'PATCH',data});
    toast('Đã lưu quyết định');await reload();
  });
}

export const pages={'register-company':registerCompany,'company-verification':companyVerification};
