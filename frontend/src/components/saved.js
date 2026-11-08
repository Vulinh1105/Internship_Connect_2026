import {api} from '../api/client.js';
import {esc, toast} from './ui.js';

export const heartIcon = '<svg aria-hidden="true" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/></svg>';

// Tập id các tin người dùng đã lưu (rỗng nếu chưa đăng nhập hoặc không tải được).
export async function savedIds(user) {
  if (!user) return new Set();
  try { return new Set((await api('/jobs/saved')).map(job => job.id)); }
  catch { return new Set(); }
}

const heartLabel = (title, on) => (on ? 'Bỏ lưu tin ' : 'Lưu tin ') + title;

// Nút trái tim trên thẻ tin. Đã lưu: tim đỏ, đặc.
export const heartButton = (id, title, on) => '<button type="button" class="heart' + (on ? ' is-saved' : '') + '" data-heart="' + Number(id)
  + '" data-title="' + esc(title) + '" aria-pressed="' + Boolean(on) + '" aria-label="' + esc(heartLabel(title, on)) + '">' + heartIcon + '</button>';

// Nút "Lưu tin" có chữ, dùng ở trang chi tiết.
export const saveButton = (id, title, on) => '<button type="button" class="secondary save-btn' + (on ? ' is-saved' : '') + '" data-heart="' + Number(id)
  + '" data-title="' + esc(title) + '" aria-pressed="' + Boolean(on) + '">' + heartIcon + '<span class="save-label">' + (on ? 'Đã lưu' : 'Lưu tin') + '</span></button>';

function paint(button, on) {
  button.classList.toggle('is-saved', on);
  button.setAttribute('aria-pressed', String(on));
  const label = button.querySelector('.save-label');
  if (label) label.textContent = on ? 'Đã lưu' : 'Lưu tin';
  else button.setAttribute('aria-label', heartLabel(button.dataset.title || '', on));
}

// Gắn một lần cho cả trang; nút được vẽ lại sau đó vẫn hoạt động.
export function bindHearts(root, user, ids) {
  root.addEventListener('click', async event => {
    const button = event.target.closest('[data-heart]');
    if (!button || !root.contains(button)) return;
    if (!user) { location.hash = 'login'; return; }
    const id = Number(button.dataset.heart), next = !ids.has(id);
    button.disabled = true;
    try {
      await api('/jobs/' + id + '/saved?value=' + next, {method: 'PUT'});
      if (next) ids.add(id); else ids.delete(id);
      for (const other of root.querySelectorAll('[data-heart="' + id + '"]')) paint(other, next);
      toast(next ? 'Đã lưu tin' : 'Đã bỏ lưu tin');
    } catch (error) { toast(error.message); }
    finally { button.disabled = false; }
  });
}
