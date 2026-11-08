// Dropdown tùy biến: tự nâng cấp mọi <select> trên trang.
// <select> gốc vẫn nằm trong DOM (ẩn) nên FormData, sự kiện change và reset hoạt động như cũ.
let uid = 0;
const chevron = '<svg class="dd-chevron" aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>';
const text = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function labelOf(select) {
  const own = select.getAttribute('aria-label');
  if (own) return own;
  const parent = select.closest('label');
  const words = parent ? [...parent.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join(' ').trim() : '';
  return words || 'Chọn';
}

function closeAll(except) {
  for (const wrap of document.querySelectorAll('.dd.dd-open')) {
    if (wrap !== except) wrap.close?.();
  }
}
document.addEventListener('click', event => closeAll(event.target.closest('.dd')));

function enhance(select) {
  if (select.dataset.dd || select.multiple) return;
  select.dataset.dd = '1';
  const id = 'dd' + (++uid);
  const wrap = document.createElement('div');
  wrap.className = 'dd';
  wrap.innerHTML = '<button type="button" class="dd-btn" aria-haspopup="listbox" aria-expanded="false" aria-controls="' + id + '">'
    + '<span class="dd-text"></span>' + chevron + '</button>'
    + '<ul class="dd-list" id="' + id + '" role="listbox" tabindex="-1" hidden></ul>';
  select.classList.add('dd-native');
  select.tabIndex = -1;
  select.setAttribute('aria-hidden', 'true');
  select.after(wrap);
  const button = wrap.querySelector('.dd-btn');
  const label = wrap.querySelector('.dd-text');
  const list = wrap.querySelector('.dd-list');
  button.setAttribute('aria-label', labelOf(select));
  list.setAttribute('aria-label', labelOf(select));

  const options = () => [...list.querySelectorAll('.dd-opt:not([aria-disabled="true"])')];
  function build() {
    list.innerHTML = [...select.options].map(o => '<li class="dd-opt" role="option" tabindex="-1" data-value="' + text(o.value) + '"'
      + (o.disabled ? ' aria-disabled="true"' : '') + ' aria-selected="' + (o.value === select.value) + '"><span>' + text(o.textContent) + '</span></li>').join('');
  }
  function sync() {
    const chosen = select.selectedOptions[0];
    label.textContent = chosen ? chosen.textContent.trim() : '';
    button.classList.toggle('is-placeholder', !select.value);
    button.disabled = select.disabled;
    for (const item of list.querySelectorAll('.dd-opt')) item.setAttribute('aria-selected', String(item.dataset.value === select.value));
  }
  function open() {
    if (select.disabled) return;
    closeAll(wrap);
    build();
    list.hidden = false;
    wrap.classList.add('dd-open');
    button.setAttribute('aria-expanded', 'true');
    const box = list.getBoundingClientRect();
    const room = window.innerHeight - button.getBoundingClientRect().bottom;
    wrap.classList.toggle('dd-up', box.height > room && button.getBoundingClientRect().top > room);
    (list.querySelector('[aria-selected="true"]') || options()[0])?.focus();
    list.querySelector('[aria-selected="true"]')?.scrollIntoView({block: 'nearest'});
  }
  function close(focus = false) {
    list.hidden = true;
    wrap.classList.remove('dd-open', 'dd-up');
    button.setAttribute('aria-expanded', 'false');
    if (focus) button.focus();
  }
  function choose(item) {
    if (!item || item.getAttribute('aria-disabled') === 'true') return;
    const changed = select.value !== item.dataset.value;
    select.value = item.dataset.value;
    sync();
    close(true);
    if (changed) select.dispatchEvent(new Event('change', {bubbles: true}));
  }
  wrap.close = close;

  button.addEventListener('click', () => wrap.classList.contains('dd-open') ? close() : open());
  button.addEventListener('keydown', event => {
    if (['ArrowDown', 'ArrowUp'].includes(event.key)) { event.preventDefault(); open(); }
  });
  list.addEventListener('click', event => choose(event.target.closest('.dd-opt')));
  list.addEventListener('keydown', event => {
    const items = options(), at = items.indexOf(document.activeElement);
    const move = n => { event.preventDefault(); items[(n + items.length) % items.length]?.focus(); };
    if (event.key === 'ArrowDown') move(at + 1);
    else if (event.key === 'ArrowUp') move(at - 1);
    else if (event.key === 'Home') move(0);
    else if (event.key === 'End') move(items.length - 1);
    else if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); choose(document.activeElement.closest('.dd-opt')); }
    else if (event.key === 'Escape') { event.preventDefault(); close(true); }
    else if (event.key === 'Tab') close();
  });

  // <label> bao ngoài sẽ chuyển click vào <select> ẩn, nên mở dropdown thay thế.
  const host = select.closest('label');
  host?.addEventListener('click', event => {
    if (event.target.closest('.dd')) return;
    event.preventDefault();
    button.focus();
    wrap.classList.contains('dd-open') ? close() : open();
  });
  select.addEventListener('change', sync);
  select.form?.addEventListener('reset', () => setTimeout(sync));
  build();
  sync();
}

export function enhanceSelects(root = document) {
  for (const select of root.querySelectorAll('select:not([data-dd])')) enhance(select);
}

export function watchSelects(root) {
  let queued = false;
  new MutationObserver(() => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; enhanceSelects(root); });
  }).observe(root, {childList: true, subtree: true});
  enhanceSelects(root);
}
