(() => {
  'use strict';
  const labels = JSON.parse(document.querySelector('#runtime-labels').textContent);
  const status = document.querySelector('#runtime-status');
  let pending = false;
  async function act(action, values = {}) {
    if (pending) return;
    pending = true;
    status.classList.add('visually-hidden');
    if (['search', 'more', 'retry'].includes(action)) {
      document.documentElement.classList.add('prairie-search-busy');
    }
    document.querySelector('main').setAttribute('aria-busy', 'true');
    const controls = [...document.querySelectorAll('button, input')];
    controls.forEach(control => control.disabled = true);
    status.textContent = action === 'theme' ? '' : action === 'language' ? labels.translating : labels.searching;
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
      history.replaceState(null, '', '/');
    } catch (error) {
      status.classList.remove('visually-hidden');
      status.textContent = error.name === 'TimeoutError' ? labels.failure + '. ' + labels.unavailable : error.message;
    } finally {
      pending = false;
      document.documentElement.classList.remove('prairie-search-busy');
      document.querySelector('main')?.removeAttribute('aria-busy');
      controls.forEach(control => control.disabled = false);
    }
  }
  document.querySelector('#search-form').addEventListener('submit', event => {
    event.preventDefault();
    const query = document.querySelector('#query').value;
    if (query.trim()) act('search', {query});
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
