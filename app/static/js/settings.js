(function () {
  'use strict';
  const { api, toast, $, h } = dab;
  const on = (id, fn) => { const el = $(id); if (el) el.addEventListener('click', fn); return el; };
  const wrap = (fn) => async (...a) => { try { await fn(...a); } catch (e) { toast(e.message, true); } };

  // OpenAI key
  const setStatus = (r) => { const s = $('#key-status'); s.textContent = r.configured ? 'configured' + (r.from_env ? ' (from environment)' : '') : 'not configured'; s.className = 'pill ' + (r.configured ? 'ok' : 'bad'); };
  on('#save-key', wrap(async () => { const r = await api('POST', '/ui/openai-key', { key: $('#openai-key').value }); $('#openai-key').value = ''; setStatus(r); toast('Key saved'); }));
  on('#clear-key', wrap(async () => { setStatus(await api('POST', '/ui/openai-key', { key: '' })); toast('Key removed'); }));

  // Tokens
  async function loadTokens() {
    const r = await api('GET', '/ui/tokens');
    $('#tok-list').replaceChildren(...r.items.map((t) => h('tr', {},
      h('td', {}, t.name, ' ', h('span', { class: 'muted small' }, t.prefix + '…')), h('td', {}, t.revoked ? h('span', { class: 'pill bad' }, 'revoked') : t.scope),
      h('td', { class: 'small muted' }, t.created_at), h('td', { class: 'small muted' }, t.last_used_at || 'never'),
      h('td', {}, t.revoked ? '' : h('button', { class: 'btn ghost sm', onclick: wrap(async () => { if (confirm('Revoke this token?')) { await api('DELETE', '/ui/tokens/' + t.id); loadTokens(); } }) }, 'Revoke')))));
  }
  on('#tok-create', wrap(async () => {
    const r = await api('POST', '/ui/tokens', { name: $('#tok-name').value, scope: $('#tok-scope').value });
    const n = $('#tok-new'); n.classList.remove('hidden');
    n.replaceChildren('Copy this token now, it is never shown again: ', h('code', {}, r.token), ' ', h('button', { class: 'btn ghost sm', onclick: () => dab.copy(r.token) }, 'Copy'));
    $('#tok-name').value = ''; loadTokens();
  }));

  // Backups
  async function loadBackups() {
    const r = await api('GET', '/ui/backups');
    $('#bk-enabled').checked = r.config.enabled; $('#bk-schedule').value = r.config.schedule; $('#bk-keep').value = r.config.keep;
    $('#bk-list').replaceChildren(...r.items.map((b) => h('tr', {}, h('td', {}, h('code', {}, b.name)), h('td', { class: 'small muted' }, (b.size / 1024).toFixed(0) + ' KB'),
      h('td', { class: 'small muted' }, b.created),
      h('td', { class: 'row', style: 'justify-content:flex-end' }, h('a', { class: 'btn ghost sm', href: '/ui/backups/' + encodeURIComponent(b.name) }, 'Export'),
        h('button', { class: 'btn ghost sm', onclick: wrap(async () => { if (confirm('Delete this backup?')) { await api('DELETE', '/ui/backups/' + encodeURIComponent(b.name)); loadBackups(); } }) }, 'Delete')))));
  }
  on('#bk-save', wrap(async () => { await api('POST', '/ui/backups/config', { enabled: $('#bk-enabled').checked, schedule: $('#bk-schedule').value, keep: Number($('#bk-keep').value) || 7 }); toast('Backup settings saved'); }));
  on('#bk-now', wrap(async () => { await api('POST', '/ui/backups'); toast('Backup created'); loadBackups(); }));
  const file = $('#bk-file');
  if (file) file.addEventListener('change', wrap(async () => {
    if (!file.files[0] || !confirm('Restore this backup? Current data is replaced (a safety copy is made first) and you will sign in again.')) { file.value = ''; return; }
    const fd = new FormData(); fd.append('file', file.files[0]);
    await api('POST', '/ui/backups/restore', fd); location.href = '/login';
  }));

  // Wizard defaults
  const defaults = JSON.parse($('#defaults').dataset.defaults);
  for (const k of ['tool', 'weight', 'design', 'user_mode', 'github_owner', 'backup_schedule']) { const el = $('#d-' + k); if (el && defaults[k] !== undefined) el.value = defaults[k]; }
  for (const k of ['backup', 'staging', 'hermes', 'api_managed']) { const el = $('#d-' + k); if (el) el.checked = !!defaults[k]; }
  on('#d-save', wrap(async () => {
    const out = {};
    for (const k of ['tool', 'weight', 'design', 'user_mode', 'github_owner', 'backup_schedule']) out[k] = $('#d-' + k).value;
    for (const k of ['backup', 'staging', 'hermes', 'api_managed']) out[k] = $('#d-' + k).checked;
    if (out.hermes) out.api_managed = true;
    await api('POST', '/ui/wizard-defaults', out); toast('Defaults saved');
  }));

  loadTokens().catch(() => {}); loadBackups().catch(() => {});
})();
