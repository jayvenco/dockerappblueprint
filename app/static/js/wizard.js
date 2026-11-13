(function () {
  'use strict';
  const { h, api, toast, $ } = dab;
  const init = JSON.parse($('#wizard-init').textContent);
  const state = Object.assign({}, init.initial);
  let schema, steps, idx = 0, followups = [], logos = [];

  const box = $('#wizard'), bar = $('#progress'), back = $('#btn-back'), next = $('#btn-next');

  function visible(field) {
    const c = field.show_if; if (!c) return true;
    const v = state[c.key];
    if ('eq' in c) return v === c.eq;
    if ('not' in c) return v !== c.not;
    return true;
  }

  function fieldEl(f) {
    const id = 'f-' + f.key;
    if (f.type === 'text' || f.type === 'number') {
      return h('div', {}, h('label', { class: 'f', for: id }, f.label),
        h('input', { id, type: f.type === 'number' ? 'number' : 'text', value: state[f.key] ?? '', placeholder: f.placeholder || '', min: f.min, max: f.max,
          oninput: (e) => { state[f.key] = f.type === 'number' ? Number(e.target.value) : e.target.value; } }));
    }
    if (f.type === 'textarea') {
      return h('div', {}, h('label', { class: 'f', for: id }, f.label),
        h('textarea', { id, placeholder: f.placeholder || '', oninput: (e) => { state[f.key] = e.target.value; } }, state[f.key] || ''));
    }
    if (f.type === 'choice') {
      return h('fieldset', { style: 'border:0;padding:0;margin:14px 0 0' }, h('legend', { class: 'f', style: 'padding:0' }, f.label),
        h('div', { class: 'choices' }, f.options.map((o) => h('label', { class: 'choice' },
          h('input', { type: 'radio', name: f.key, value: String(o.value), checked: state[f.key] === o.value,
            onchange: () => { state[f.key] = o.value; render(); } }),
          h('b', {}, o.label, o.recommended ? h('em', { class: 'rec' }, 'Recommended') : null), h('span', {}, o.desc)))));
    }
    if (f.type === 'toggle') {
      return h('label', { class: 'toggle' },
        h('input', { type: 'checkbox', checked: !!state[f.key], onchange: (e) => { state[f.key] = e.target.checked; if (f.key === 'hermes' && e.target.checked) state.api_managed = true; render(); } }),
        h('span', {}, h('b', {}, f.label), h('br'), h('span', { class: 'muted small' }, f.desc || '')));
    }
    if (f.type === 'list') {
      const list = state[f.key] = state[f.key] || [];
      const rows = list.map((it, i) => h('div', { class: 'item-row' },
        f.item_fields.map((sf) => h('input', { type: 'text', 'aria-label': sf.label, placeholder: sf.placeholder, value: it[sf.key] || '', oninput: (e) => { it[sf.key] = e.target.value; } })),
        h('button', { class: 'btn ghost sm', type: 'button', 'aria-label': 'Remove', onclick: () => { list.splice(i, 1); render(); } }, 'Remove')));
      return h('div', {}, h('p', { class: 'muted' }, 'Leave empty if none.'), rows,
        h('button', { class: 'btn ghost sm', type: 'button', onclick: () => { list.push({ name: '', purpose: '' }); render(); } }, '+ Add an API'));
    }
    return h('div');
  }

  function stepBasic(step) {
    return [h('h2', { style: 'margin-top:0' }, step.title), h('p', { class: 'muted' }, step.help), step.fields.filter(visible).map(fieldEl)];
  }

  function stepLogo() {
    const desc = h('textarea', { id: 'logo-desc', placeholder: 'e.g. a friendly blue whale carrying a shipping container, flat vector', oninput: (e) => { state._logo_desc = e.target.value; } }, state._logo_desc || '');
    const grid = h('div', { class: 'logos' }, logos.map((l) => h('label', {},
      h('img', { src: l.image_url, alt: 'Logo variant ' + l.id }),
      h('input', { type: 'radio', name: 'logo', checked: state._logo_id === l.id, onchange: () => { state._logo_id = l.id; state.logo = 'logo.png'; } }), ' Use',
      h('div', { class: 'small' }, h('a', { href: l.image_url, download: 'logo.png' }, 'PNG'), ' · ', h('a', { href: l.icon_url, download: 'icon.png' }, '256 icon')))));
    const go = h('button', { class: 'btn', type: 'button', id: 'logo-go', onclick: async () => {
      go.disabled = true; go.textContent = 'Generating…';
      try { const r = await api('POST', '/api/v1/logos', { description: state._logo_desc || state.purpose || state.app_name, n: 3 }); logos = r.items.concat(logos); }
      catch (e) { toast(e.message, true); }
      render();
    } }, 'Generate 3 variants');
    return [h('h2', { style: 'margin-top:0' }, 'Logo (optional)'),
      h('p', { class: 'muted' }, 'Generate a logo with OpenAI, pick one and download the PNG and 256px icon. Place them in the project as docs/logo.png and unraid/icon.png. Skip this step if you do not need one.'),
      h('label', { class: 'f', for: 'logo-desc' }, 'Describe the logo'), desc, h('p', {}, go), grid];
  }

  function stepReview() {
    const ex = state.external_apis.map((a) => a.name + (a.purpose ? ' (' + a.purpose + ')' : '')).join(', ') || 'none';
    const sum = [['App', state.app_name], ['Tool', state.tool === 'codex' ? 'OpenAI Codex' : 'Claude Code'], ['Weight / design', state.weight + ' / ' + state.design],
      ['Users', state.user_mode + (state.hermes ? ', Hermes Agent' : '') + (state.api_managed ? ', API management' : '')], ['External APIs', ex],
      ['Database', state.database], ['Backups', state.backup ? state.backup_schedule + ', keep ' + state.backup_keep : 'no'],
      ['Containers', state.containers], ['Staging + production', state.staging ? 'yes' : 'no'], ['GitHub account', state.github_owner]];
    const fq = followups.length ? [h('h3', {}, 'A few follow-up questions'), h('p', { class: 'muted small' }, 'Optional, but they make the prompt sharper.'),
      followups.map((q) => h('div', {}, h('label', { class: 'f', for: 'q-' + q.id }, q.question),
        h('input', { id: 'q-' + q.id, type: 'text', value: state.followups[q.id] || '', oninput: (e) => { state.followups[q.id] = e.target.value; } })))] : [];
    const imp = schema.improvements.map((i) => h('label', { class: 'toggle' },
      h('input', { type: 'checkbox', checked: state.improvements.includes(i.id), onchange: (e) => {
        state.improvements = state.improvements.filter((x) => x !== i.id); if (e.target.checked) state.improvements.push(i.id); } }),
      h('span', {}, h('b', {}, i.label), h('br'), h('span', { class: 'muted small' }, i.reason))));
    return [h('h2', { style: 'margin-top:0' }, 'Review'),
      h('table', {}, sum.map((r) => h('tr', {}, h('th', {}, r[0]), h('td', {}, r[1])))),
      fq, h('h3', {}, 'Improvement suggestions'), h('p', { class: 'muted small' }, 'Selected items are added to the prompt.'), imp];
  }

  function render() {
    bar.replaceChildren(...steps.map((_, i) => h('i', { class: i < idx ? 'done' : i === idx ? 'now' : '' })));
    const s = steps[idx];
    box.replaceChildren(...[s.id === 'logo' ? stepLogo() : s.id === 'review' ? stepReview() : stepBasic(s)].flat(Infinity));
    back.style.visibility = idx === 0 ? 'hidden' : 'visible';
    next.textContent = idx === steps.length - 1 ? (init.editing ? 'Save and regenerate' : 'Generate prompt') : 'Next';
  }

  function stepError() {
    const s = steps[idx];
    if (s.id === 'basics') {
      if (!(state.app_name || '').trim()) return 'Give the app a name.';
      if (!(state.purpose || '').trim()) return 'Describe what the app does.';
    }
    return null;
  }

  async function goNext() {
    const err = stepError(); if (err) { toast(err, true); return; }
    if (idx < steps.length - 1) {
      idx++;
      if (steps[idx].id === 'review') { try { followups = (await api('POST', '/api/v1/followups', { spec: state })).items; } catch (e) { followups = []; } }
      render(); window.scrollTo(0, 0); return;
    }
    next.disabled = true;
    const spec = Object.assign({}, state); for (const k of Object.keys(spec)) if (k.startsWith('_')) delete spec[k];
    try {
      const r = init.editing ? await api('PATCH', '/api/v1/prompts/' + init.editing, { spec }) : await api('POST', '/api/v1/prompts', { spec });
      location.href = '/prompts/' + r.id;
    } catch (e) { toast(e.message, true); next.disabled = false; }
  }

  next.addEventListener('click', goNext);
  back.addEventListener('click', () => { if (idx > 0) { idx--; render(); } });

  api('GET', '/api/v1/wizard/schema').then((s) => {
    schema = s;
    if (!state.improvements) state.improvements = s.defaults.improvements.slice();
    state.followups = state.followups || {}; state.external_apis = state.external_apis || [];
    steps = s.steps.concat([{ id: 'logo', title: 'Logo' }, { id: 'review', title: 'Review' }]);
    api('GET', '/api/v1/logos').then((l) => { logos = l.items; if (idx === steps.findIndex((x) => x.id === 'logo')) render(); }).catch(() => {});
    render();
  }).catch((e) => toast(e.message, true));
})();
