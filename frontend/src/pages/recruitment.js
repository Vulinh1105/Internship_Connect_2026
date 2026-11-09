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

const questionKinds=[['knowledge','Kiến thức chuyên môn'],['problem_solving','Giải quyết vấn đề'],['both','Cả hai']];
const questionLevels=[['basic','Cơ bản'],['intermediate','Trung bình'],['advanced','Nâng cao']];
const questionFields=(q={})=>'<fieldset class="stack" data-question><legend>Câu hỏi</legend>'
  +area('question','Nội dung',q.question,'required maxlength="350" rows="2"')
  +select('kind','Loại câu hỏi',questionKinds,q.kind)+select('difficulty','Độ khó',questionLevels,q.difficulty)
  +area('criteria','Tiêu chí tham chiếu',q.criteria,'maxlength="600" rows="2"')
  +area('guidance','Gợi ý đáp án (chỉ dùng khi chấm)',q.guidance,'maxlength="1000" rows="2"')
  +'<div class="row">'+btn('up','Lên')+btn('down','Xuống')+btn('drop','Xóa câu')+'</div></fieldset>';

async function questionSets({root,user,args,reload}){
  if(!user)return loginRequired(root);
  const endpoint='/mock-interviews/question-sets';
  const [companies,jobs,sets]=await Promise.all([api('/companies/mine'),api('/jobs/mine'),api(endpoint)]);
  const managed=companies.filter(c=>c.can_manage_members);
  const positions=jobs.filter(j=>!/^tin demo/i.test(j.title)&&(!j.details?.fixture_case||j.details.fixture_case==='baseline_public'));
  const current=sets.find(s=>s.id===Number(args[0]));
  const create=args[0]==='new';
  root.innerHTML=heading('Bộ câu hỏi phỏng vấn','Nhập tên vị trí muốn luyện phỏng vấn. Bạn có thể dùng tên một tin tuyển dụng đã đăng hoặc nhập vị trí mới.')
    +'<div class="row"><a href="#workspace">Về quản lý tuyển dụng</a>'
    +(managed.length?'<a class="button secondary" href="#question-sets/new">Tải tệp câu hỏi</a>':'')+'</div>'
    +(sets.length?sets.map(s=>box('<h3>'+esc(s.title)+'</h3>'+tags(s.job_title,s.company_name,
        !s.published?'Bản nháp':!s.job_id||positions.find(j=>j.id===s.job_id)?.active?'Đang công khai':'Ẩn vì tin chưa mở tuyển',s.questions.length+' câu')
      +'<div class="row"><a class="button secondary" href="#question-sets/'+s.id+'">Chỉnh sửa</a>'+btn('remove-set','Xóa bộ',s.id)+'</div>')).join('')
      :empty('Chưa có bộ câu hỏi.'));
  action(root,'remove-set',async id=>{
    if(!confirm('Xóa bộ câu hỏi này?'))return;
    await api(endpoint+'/'+id,{method:'DELETE'});
    if(args.length)location.hash='question-sets';else await reload();
  });
  if(create&&managed.length){
    root.insertAdjacentHTML('beforeend',box('<h2>Tải tệp câu hỏi</h2>'
      +copy('AI trích các câu có sẵn trong tài liệu kể cả khi không đánh số. Bản trích xuất được lưu nháp để bạn kiểm tra trước khi công khai.')
      +form('import-questions',select('company_id','Doanh nghiệp',managed.map(c=>[c.id,c.name]))
        +field('position_title','Tên vị trí phỏng vấn','','text','required minlength="2" maxlength="200" list="position-suggestions" placeholder="Ví dụ: Thực tập sinh Backend"')
        +'<datalist id="position-suggestions"></datalist>'
        +'<label class="field">Tệp PDF, DOCX, TXT hoặc MD (tối đa 10 MB, 20 câu)'
        +'<input type="file" name="file" accept=".pdf,.docx,.txt,.md" required></label>'
        +'<p id="import-progress" role="status" hidden></p>','Trích xuất câu hỏi')));
    const company=root.querySelector('#import-questions [name="company_id"]');
    const suggestions=root.querySelector('#position-suggestions');
    const suggest=()=>{
      const names=[...new Set(positions.filter(j=>j.company_id===Number(company.value)).map(j=>j.title))];
      suggestions.innerHTML=names.map(name=>'<option value="'+esc(name)+'"></option>').join('');
    };
    company.addEventListener('change',suggest);
    suggest();
    bindForm(root,'import-questions',async data=>{
      const progress=root.querySelector('#import-progress');
      progress.hidden=false;
      progress.textContent='Đang đọc tài liệu và trích xuất câu hỏi…';
      try{
        const draft=await api(endpoint+'/import',{method:'POST',data});
        if(!root.isConnected)return;
        toast('Đã trích xuất '+draft.questions.length+' câu. Hãy kiểm tra bản nháp.');
        location.hash='question-sets/'+draft.id;
      }catch(error){
        progress.textContent=error.message;
      }
    },{keepFiles:true});
    return;
  }
  if(!current)return;
  root.insertAdjacentHTML('beforeend',box('<h2>Sửa bộ câu hỏi</h2>'+form('question-set',
    (current.job_id?copy(current.job_title):field('position_title','Tên vị trí phỏng vấn',current.position_title,'text',
      'required minlength="2" maxlength="200"'))
    +field('title','Tên bộ câu hỏi',current.title,'text','required maxlength="160"')
    +area('description','Mô tả',current.description,'maxlength="2000"')
    +'<label><input type="checkbox" name="published" value="true" '+(current.published?'checked':'')+'> Công khai</label>'
    +'<div id="set-questions" class="stack">'+current.questions.map(questionFields).join('')+'</div>'
    +btn('add-question','Thêm câu hỏi'),'Lưu bộ câu hỏi')));
  const rows=root.querySelector('#set-questions');
  action(root,'add-question',()=>{
    if(rows.children.length>=20)throw new Error('Mỗi bộ tối đa 20 câu.');
    rows.insertAdjacentHTML('beforeend',questionFields());
    rows.lastElementChild.querySelector('textarea').focus();
  });
  rows.addEventListener('click',e=>{
    const button=e.target.closest('[data-action]');
    if(!button)return;
    const row=button.closest('[data-question]');
    if(button.dataset.action==='up'&&row.previousElementSibling)rows.insertBefore(row,row.previousElementSibling);
    if(button.dataset.action==='down'&&row.nextElementSibling)rows.insertBefore(row.nextElementSibling,row);
    if(button.dataset.action==='drop'&&rows.children.length>1)row.remove();
  });
  bindForm(root,'question-set',async data=>{
    const keys=['question','kind','difficulty','criteria','guidance'];
    const columns=keys.map(key=>data.getAll(key));
    const questions=columns[0].map((_,i)=>Object.fromEntries(keys.map((key,j)=>[key,columns[j][i]])));
    await api(endpoint+'/'+current.id,{method:'PUT',
      data:{job_id:current.job_id,company_id:current.company_id,position_title:data.get('position_title'),
        title:data.get('title'),description:data.get('description'),
        published:data.has('published'),questions}});
    toast('Đã lưu bộ câu hỏi');location.hash='question-sets';
  },{keepFiles:true});
}

export const pages={'question-sets':questionSets,'recruitment-stats':stats,'company-members':members};
