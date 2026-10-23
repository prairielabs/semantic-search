(() => {
  'use strict';
  const labels = JSON.parse(document.querySelector('#runtime-labels').textContent);
  const status = document.querySelector('#runtime-status');
  const filters = JSON.parse(document.querySelector('#runtime-filters').textContent);
  let pending = false;
  async function act(action, values = {}) {
    if (pending) return;
    pending = true;
    status.classList.add('visually-hidden');
    if (['search', 'more', 'retry'].includes(action)) {
      document.documentElement.classList.add('prairie-search-busy');
    }
    document.querySelector('main').setAttribute('aria-busy', 'true');
    const draftQuery = document.querySelector('#query').value;
    const draftFilter = document.querySelector('#filter-select').value;
    const controls = [...document.querySelectorAll('button, input, textarea, select')];
    const disabled = controls.map(control => control.disabled);
    controls.forEach(control => control.disabled = true);
    status.textContent = action === 'theme' || action.startsWith('filter_') ? '' : action === 'language' ? labels.translating : labels.searching;
    try {
      const response = await fetch('/api/action', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action, ...values}), signal: AbortSignal.timeout(310000)
      });
      const text = await response.text();
      if (!response.ok) throw new Error(text.length < 200 ? text : labels.unavailable);
      const next = new DOMParser().parseFromString(text, 'text/html');
      if (next.documentElement.dataset.prairieApp !== 'semantic-search') throw new Error(labels.unavailable);
      // The trusted local host returns the complete next document, preserving its native forms.
      document.open(); document.write(text); document.close();
      if (action.startsWith('filter_') || ['theme', 'language'].includes(action)) {
        document.querySelector('#query').value = draftQuery;
      }
      if (['theme', 'language'].includes(action)) document.querySelector('#filter-select').value = draftFilter;
      if (action.startsWith('filter_')) {
        document.querySelector('.filter-manager').open = true;
        document.querySelector('.filter-manager summary').focus();
      }
      history.replaceState(null, '', '/');
    } catch (error) {
      status.classList.remove('visually-hidden');
      status.textContent = error.name === 'TimeoutError' ? labels.failure + '. ' + labels.unavailable : error.message;
    } finally {
      pending = false;
      document.documentElement.classList.remove('prairie-search-busy');
      document.querySelector('main')?.removeAttribute('aria-busy');
      controls.forEach((control, i) => control.disabled = disabled[i]);
    }
  }
  document.querySelector('#search-form').addEventListener('submit', event => {
    event.preventDefault();
    const query = document.querySelector('#query').value;
    if (query.trim()) act('search', {query, filter_id: document.querySelector('#filter-select').value});
  });
  document.querySelector('#filter-form').addEventListener('submit', event => {
    event.preventDefault();
    act('filter_save', {filter_id: document.querySelector('#filter-id').value,
      name: document.querySelector('#filter-name').value,
      criteria: document.querySelector('#filter-criteria').value});
  });
  document.querySelector('#filter-new').addEventListener('click', () => {
    document.querySelector('#filter-form').reset();
    document.querySelector('#filter-id').value = '';
    document.querySelector('#filter-name').focus();
  });
  document.querySelectorAll('[data-filter-edit]').forEach(button => {
    button.addEventListener('click', () => {
      const filter = filters.find(item => item.id === button.dataset.filterEdit);
      if (!filter) return;
      document.querySelector('#filter-id').value = filter.id;
      document.querySelector('#filter-name').value = filter.name;
      document.querySelector('#filter-criteria').value = filter.criteria;
      document.querySelector('#filter-name').focus();
    });
  });
  document.querySelectorAll('[data-filter-delete]').forEach(button => {
    button.addEventListener('click', () => act('filter_delete', {filter_id: button.dataset.filterDelete}));
  });
  document.querySelector('#language-form').addEventListener('submit', event => {
    event.preventDefault();
    const language = document.querySelector('#language-input').value;
    if (language.trim()) act('language', {language});
  });
  document.querySelector('[data-prairie-action="toggle-theme"]').addEventListener('click', () => act('theme'));
  document.querySelectorAll('[data-runtime-action]').forEach(button => {
    button.addEventListener('click', () => act(button.dataset.runtimeAction));
  });
})();
