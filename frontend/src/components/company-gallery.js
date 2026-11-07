import {esc} from './ui.js';

const commons='https://commons.wikimedia.org/wiki/File:';
const license='https://creativecommons.org/licenses/by-sa/4.0/';
const asset=name=>new URL('../../assets/'+name+'.webp',import.meta.url).href;

const photos=[
  {name:'Techcombank', file:'techcombank', alt:'Trụ sở Techcombank trên phố Quang Trung, Hà Nội', author:'Newone',
    source:commons+'NewOne_-_Techcombank_Head_Office_with_4_VinFast_EV.jpg', sector:'Tài chính · Ngân hàng'},
  {name:'Viettel', file:'viettel', alt:'Tòa nhà văn phòng Viettel tại Tây Hồ, Hà Nội năm 2015', author:'Vuong Tri Binh',
    source:commons+'Viettel_Group_office_building_at_Tay_Ho_in_2015.jpg', sector:'Công nghệ · Viễn thông'},
  {name:'Lotte Center Hanoi', file:'lotte', alt:'Tòa tháp Lotte Center Hanoi tại Hà Nội', author:'NKSTTSSHNVN',
    source:commons+'Lotte_Tower_Hanoi_-_NKS.jpg', sector:'Thương mại · Dịch vụ'},
];

function credit(photo){
  return '<a href="'+photo.source+'" target="_blank" rel="noopener noreferrer">'+esc(photo.author)+'</a>'
    +' / <a href="'+license+'" target="_blank" rel="noopener noreferrer">CC BY-SA 4.0</a>';
}

export function heroPhoto(){
  const photo=photos[0];
  return '<figure class="hero-photo"><img src="'+asset(photo.file)+'" alt="'+esc(photo.alt)
    +'" width="1440" height="810" fetchpriority="high"><figcaption><span><b>'+esc(photo.name)
    +'</b><span>Trụ sở tại Hà Nội</span></span><small>'+credit(photo)+' · Ảnh thu nhỏ, cắt khung</small></figcaption></figure>';
}

export function companyGallery(){
  return '<section class="section company-gallery" aria-labelledby="company-gallery-title">'
    +'<div class="section-heading"><div><p class="eyebrow">Góc nhìn doanh nghiệp</p>'
    +'<h2 id="company-gallery-title">Không gian làm việc thực tế</h2>'
    +'<p class="muted">Bộ ảnh tham khảo về các địa điểm làm việc tại Việt Nam, tách riêng với danh sách tuyển dụng mẫu.</p></div></div>'
    +'<div class="grid gallery-grid">'+photos.map(photo=>'<figure class="company-photo">'
      +'<img src="'+asset(photo.file)+'" alt="'+esc(photo.alt)+'" loading="lazy" decoding="async">'
      +'<figcaption><span class="eyebrow">'+esc(photo.sector)+'</span><h3>'+esc(photo.name)+'</h3><small>'+credit(photo)
      +' · Ảnh thu nhỏ, cắt khung</small></figcaption></figure>').join('')+'</div></section>';
}
