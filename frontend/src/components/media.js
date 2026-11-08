import {esc} from './ui.js';

const asset=path=>new URL('../../assets/'+path,import.meta.url).href;

// Banner trang chủ: đặt ảnh vào frontend/assets/banners/ rồi thêm một dòng cho mỗi ảnh, ví dụ:
// {src:asset('banners/banner-1.webp'),alt:'Mô tả ảnh',href:'#jobs'},
export const banners=[
];

// Logo doanh nghiệp: đặt ảnh vào frontend/assets/logos/ với tên company-<id>.webp (id của doanh nghiệp, ví dụ company-1.webp).
// Chưa có ảnh thì hiện chữ cái đầu của tên doanh nghiệp.
export const logoTile=(id,name,large=false)=>'<span class="logo-tile'+(large?' logo-lg':'')+'"><span aria-hidden="true">'
  +esc(String(name||'?').trim().charAt(0).toUpperCase())+'</span><img src="'+asset('logos/company-'+id+'.webp')
  +'" alt="" loading="lazy" onerror="this.remove()"></span>';

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
