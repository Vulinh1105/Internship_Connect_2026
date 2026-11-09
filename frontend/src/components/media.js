import {esc} from './ui.js';

const asset=path=>new URL('../../assets/'+path,import.meta.url).href;

// Banner trang chủ: đặt ảnh vào frontend/assets/banners/ rồi thêm một dòng cho mỗi ảnh, ví dụ:
// {src:asset('banners/banner-1.webp'),alt:'Mô tả ảnh',href:'#jobs'},
export const banners=[
  {src:asset('banners/career-illustration.png'),alt:'Minh họa khám phá cơ hội nghề nghiệp',href:'#jobs'},
];

const companyMedia={
  'NovaBridge Digital':[36706460,'circuit-board'],
  'GreenPeak Finance':[7845375,'mountain'],
  'Horizon Logistics':[30625284,'truck'],
  'BrightPath Education':[8617741,'graduation-cap'],
  'BlueRiver Commerce':[7691724,'waves'],
  'Atlas Data Lab':[37828832,'database'],
  'Sunrise Retail':[24862481,'sunrise'],
  'FutureWorks Consulting':[7433874,'compass'],
  'Lotus Media House':[10375955,'flower-2'],
  'CloudNest Solutions':[34804001,'cloud'],
  'Mekong AgriTech':[8342806,'sprout'],
  'UrbanSpace Design':[17115287,'building-2'],
  'VietLink Supply':[38195854,'package-open'],
  'NextWave Fintech':[7964426,'chart-no-axes-combined'],
  'EduSphere Academy':[37811262,'book-open'],
  'EcoMotion Energy':[29146655,'zap'],
  'CareConnect Health':[7163395,'heart-pulse'],
  'PrimeAudit Advisory':[7688454,'shield-check'],
  'MarketSpring Research':[36733318,'chart-pie'],
  'TalentLoop HR':[3865847,'users-round'],
};

export function companyPhoto(name,credit=false){
  const photo=companyMedia[name]?.[0];
  if(!photo)return '';
  return '<figure class="company-cover"><img src="'+esc(asset('companies/'+photo+'.jpg'))
    +'" alt="Ảnh minh họa môi trường làm việc" loading="lazy" decoding="async">'
    +(credit?'<figcaption>Ảnh minh họa · <a href="https://www.pexels.com/photo/'+photo+'/" target="_blank" rel="noopener noreferrer">Pexels</a></figcaption>':'')+'</figure>';
}

// Ưu tiên logo doanh nghiệp tải lên, rồi dùng biểu tượng mẫu nếu có.
export function logoTile(id,name,large=false,hasLogo=false){
  const symbol=companyMedia[name]?.[1];
  return '<span class="logo-tile'+(large?' logo-lg':'')+'"><span aria-hidden="true">'
    +esc(String(name||'?').trim().charAt(0).toUpperCase())+'</span>'
    +(symbol?'<img src="'+esc(asset('company-logos/'+symbol+'.svg'))+'" alt="" loading="lazy">':'')
    +(hasLogo?'<img src="/api/companies/'+Number(id)+'/logo" alt="" loading="lazy" onerror="this.remove()">':'')+'</span>';
}

export const bannerHtml=()=>banners.length
  ?'<div class="banner">'+banners.map((b,i)=>'<a class="banner-slide" href="'+esc(b.href||'#jobs')+'"'+(i?' hidden':'')+'><img src="'+esc(b.src)+'" alt="'+esc(b.alt||'')+'"></a>').join('')
    +(banners.length>1?'<button type="button" class="banner-nav prev" aria-label="Ảnh trước">‹</button><button type="button" class="banner-nav next" aria-label="Ảnh sau">›</button>':'')+'</div>'
  :'<div class="banner banner-empty" aria-hidden="true"></div>';

export function bindBanner(root){
  const slides=[...root.querySelectorAll('.banner-slide')];
  if(slides.length<2)return;
  let at=0;
  const go=n=>{slides[at].hidden=true;at=(n+slides.length)%slides.length;slides[at].hidden=false;};
  root.querySelector('.banner-nav.prev')?.addEventListener('click',()=>go(at-1));
  root.querySelector('.banner-nav.next')?.addEventListener('click',()=>go(at+1));
}
