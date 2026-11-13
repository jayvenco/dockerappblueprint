(function () {
  'use strict';
  const { h, $ } = dab;
  $('#base-url').textContent = location.origin + '/api/v1';
  fetch('/api/openapi.json').then((r) => r.json()).then((spec) => {
    const rows = [];
    for (const [path, ops] of Object.entries(spec.paths)) {
      for (const [method, op] of Object.entries(ops)) {
        rows.push(h('div', { class: 'endpoint' }, h('span', { class: 'method' }, method.toUpperCase()), h('code', {}, path),
          h('span', { class: 'muted small' }, op.summary || '')));
      }
    }
    $('#endpoints').replaceChildren(...rows);
  }).catch(() => { $('#endpoints').textContent = 'Could not load the API spec.'; });
})();
