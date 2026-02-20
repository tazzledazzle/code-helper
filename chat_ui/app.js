/**
 * Code Helper Chat UI — minimal client for POST /chat.
 * API base: set window.CODE_HELPER_API before loading, or use ?api=http://localhost:8000, or default below.
 */
(function () {
  const params = new URLSearchParams(window.location.search);
  const API_BASE = window.CODE_HELPER_API || params.get('api') || 'http://localhost:8000';

  const form = document.getElementById('chat-form');
  const messageInput = document.getElementById('message');
  const projectPathInput = document.getElementById('project_path');
  const sendBtn = document.getElementById('send-btn');
  const responseEl = document.getElementById('response');

  function setLoading(loading) {
    sendBtn.disabled = loading;
    responseEl.textContent = loading ? 'Sending…' : '';
    responseEl.className = loading ? 'loading' : '';
  }

  function setError(msg) {
    responseEl.textContent = 'Error: ' + msg;
    responseEl.className = 'error';
  }

  function setResponse(text) {
    responseEl.textContent = text || '(empty response)';
    responseEl.className = '';
  }

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    const message = (messageInput.value || '').trim();
    if (!message) return;

    const projectPath = (projectPathInput.value || '').trim() || undefined;
    const url = API_BASE.replace(/\/$/, '') + '/chat';
    const body = { message };
    if (projectPath) body.project_path = projectPath;

    setLoading(true);
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(function () { return {}; });
      if (!res.ok) {
        setError(data.detail || data.message || 'Request failed');
        return;
      }
      setResponse(data.response);
    } catch (err) {
      setError(err.message || 'Network error');
    } finally {
      setLoading(false);
    }
  });
})();
