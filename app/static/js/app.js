(function () {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  window.dab = {
    $,
    async api(method, url, body, raw) {
      const opt = { method, headers: {}, credentials: 'same-origin' };
      if (body !== undefined && !(body instanceof FormData)) { opt.headers['Content-Type'] = 'application/json'; opt.body = JSON.stringify(body); }
      if (body instanceof FormData) opt.body = body;
      const r = await fetch(url, opt);
      if (raw) return r;
      let data = null; try { data = await r.json(); } catch (e) { /* no body */ }
      if (!r.ok) {
        let d = data && data.detail;
        if (d && typeof d === 'object') d = (d.errors || [JSON.stringify(d)]).join('; ');
        throw new Error(d || ('Request failed (' + r.status + ')'));
      }
      return data;
    },
    toast(msg, bad) {
      const t = document.createElement('div'); t.className = 'toast'; t.setAttribute('role', 'status');
      if (bad) t.style.borderColor = 'var(--bad)'; t.textContent = msg; document.body.appendChild(t);
      setTimeout(() => t.remove(), 4200);
    },
    h(tag, attrs, ...kids) {
      const el = document.createElement(tag);
      for (const [k, v] of Object.entries(attrs || {})) {
        if (v === false || v == null) continue;
        if (k === 'class') el.className = v; else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
        else if (k === 'value') el.value = v; else el.setAttribute(k, v === true ? '' : v);
      }
      for (const k of kids.flat()) if (k != null && k !== false) el.append(k.nodeType ? k : document.createTextNode(String(k)));
      return el;
    },
    async copy(text) {
      try { await navigator.clipboard.writeText(text); }
      catch (e) { const ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove(); }
      dab.toast('Copied to clipboard');
    },
  };

  // Theme and font selectors (header + settings): apply immediately, then persist.
  document.querySelectorAll('[data-appearance]').forEach((sel) => {
    sel.addEventListener('change', async () => {
      const kind = sel.dataset.appearance;
      document.documentElement.dataset[kind] = sel.value;
      document.querySelectorAll('[data-appearance="' + kind + '"]').forEach((o) => { o.value = sel.value; });
      if (!$('.nav a')) return; // login page: nothing to persist
      try { await dab.api('POST', '/ui/appearance', { [kind]: sel.value }); } catch (e) { dab.toast(e.message, true); }
    });
  });

  // Prompt page: copy buttons
  const cp = $('#copy-prompt'); if (cp) cp.addEventListener('click', () => dab.copy($('#prompt-text').textContent));
  const cc = $('#copy-context'); if (cc) cc.addEventListener('click', () => dab.copy($('#context-text').textContent));

  // Home: delete + import
  document.querySelectorAll('[data-delete-prompt]').forEach((b) => b.addEventListener('click', async () => {
    if (!confirm('Delete this prompt?')) return;
    try { await dab.api('DELETE', '/api/v1/prompts/' + b.dataset.deletePrompt); location.reload(); } catch (e) { dab.toast(e.message, true); }
  }));
  const imp = $('[data-import-prompts]');
  if (imp) imp.addEventListener('change', async () => {
    try {
      const data = JSON.parse(await imp.files[0].text());
      const r = await dab.api('POST', '/api/v1/prompts/import', data);
      dab.toast('Imported ' + r.imported + ' prompt(s)'); setTimeout(() => location.reload(), 700);
    } catch (e) { dab.toast('Import failed: ' + e.message, true); }
  });
})();
