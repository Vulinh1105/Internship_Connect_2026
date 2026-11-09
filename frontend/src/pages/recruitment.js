import {api} from '../api/client.js';
import {action, area, bindForm, box, btn, copy, empty, esc, field, form, heading, select, tags, toast} from '../components/ui.js';
import {loginRequired} from './public.js';

async function stats({root,user}){
  if(!user)return loginRequired(root);
  const rows=await api('/recruitment/stats');
  const titles=['Tin tuyển dụng','Lượt xem','Hồ sơ đã nộp','Chờ xử lý','Đã mời phỏng vấn','Đã nhận','Tỷ lệ ứng tuyển'];
  root.innerHTML=heading('Thống kê tuyển dụng','Tỷ lệ ứng tuyển được tính bằng số hồ sơ đã nộp chia cho lượt xem đã ghi nhận.')
    +(rows.length?'<div class="table-wrap"><table><thead><tr>'+titles.map(t=>'<th scope="col">'+esc(t)+'</th>').join('')
      +'</tr></thead><tbody>'+rows.map(r=>'<tr>'+[r.title,r.views,r.total,r.pending,r.invited,r.accepted,r.conversion==null?'—':r.conversion+'%']
        .map(v=>'<td>'+esc(v)+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>':empty());
}

async function members({root,user,reload}){
  if(!user)return loginRequired(root);
  const companies=(await api('/companies/mine')).filter(c=>c.can_manage_members);
  const lists=await Promise.all(companies.map(c=>api('/companies/'+c.id+'/members')));
  root.innerHTML=heading('Thành viên doanh nghiệp')+(companies.length?companies.map((c,i)=>box('<h2>'+esc(c.name)+'</h2>'
    +lists[i].map(m=>'<div class="row">'+esc(m.email)+tags(m.manager?'Quản lý':m.active?'Thành viên':'Đã thu hồi')
      +(m.active&&!m.manager?btn('revoke-member','Thu hồi',c.id+'/'+m.id):'')+'</div>').join('')
    +form('member-'+c.id,field('email','Email thành viên','','email','required maxlength="255"'),'Thêm hoặc mời thành viên'))).join('')
    :empty('Bạn chưa quản lý doanh nghiệp nào.'));
  for(const c of companies)bindForm(root,'member-'+c.id,async data=>{
    await api('/companies/'+c.id+'/members',{method:'POST',data});toast('Đã lưu thành viên');await reload();
  });
  action(root,'revoke-member',async value=>{
    if(!confirm('Thu hồi quyền truy cập doanh nghiệp?'))return;
    const [company,member]=value.split('/');
    await api('/companies/'+company+'/members/'+member,{method:'DELETE'});await reload();
  });
}

async function overview({root,user,reload}){
  if(!user)return loginRequired(root);
  const data=await api('/admin/overview');
  const titles={users:'Tài khoản',companies:'Doanh nghiệp',jobs:'Tin tuyển dụng',applications:'Đơn ứng tuyển'};
  root.innerHTML=heading('Tổng quan quản trị')
    +'<div class="stat-grid">'+Object.entries(data.counts).map(([key,total])=>'<div class="stat"><strong>'+esc(total)+'</strong><span>'+esc(titles[key])+'</span></div>').join('')+'</div>'
    +'<h2>Báo cáo tin tuyển dụng</h2>'+(data.reports.length?data.reports.map(r=>box('<h3>'+esc(r.title)+'</h3>'+copy(r.reason)
      +form('report-'+r.id,select('status','Kết quả',[['resolved','Đã xử lý'],['dismissed','Bác báo cáo']])
        +area('note','Ghi chú xử lý','','required maxlength="2000"'),'Lưu kết quả'))).join(''):empty('Không có báo cáo đang chờ.'))
    +'<h2>Đánh giá doanh nghiệp</h2>'+(data.reviews.length?data.reviews.map(r=>box('<h3>'+esc(r.company)+'</h3>'
      +tags(r.student_rating+'/5',r.review_status==='approved'?'Đã công khai':'Chờ duyệt')+copy(r.student_review)
      +(r.review_status==='approved'?'':btn('approve-review','Duyệt',r.application_id))+btn('reject-review',r.review_status==='approved'?'Gỡ':'Từ chối',r.application_id))).join('')
      :empty('Chưa có đánh giá đang chờ hoặc công khai.'))
    +'<h2>Yêu cầu tài khoản</h2>'+(data.closure_requests.length?data.closure_requests.map(r=>box(copy(r.email)
      +tags(r.action==='delete'?'Yêu cầu xóa dữ liệu':'Yêu cầu vô hiệu hóa')
      +btn('disable-account','Vô hiệu hóa tài khoản',r.id))).join(''):empty('Chưa có yêu cầu.'));
  for(const r of data.reports)bindForm(root,'report-'+r.id,async data=>{
    await api('/admin/job-reports/'+r.id,{method:'PATCH',data});await reload();
  });
  for(const [name,status] of [['approve-review','approved'],['reject-review','rejected']])action(root,name,async id=>{
    await api('/admin/company-reviews/'+id,{method:'PATCH',data:{status}});await reload();
  });
  action(root,'disable-account',async id=>{
    if(!confirm('Vô hiệu hóa đăng nhập của tài khoản này?'))return;
    await api('/admin/account-closures/'+id,{method:'POST'});await reload();
  });
}
export const pages={'recruitment-stats':stats,'company-members':members,'admin-overview':overview};
