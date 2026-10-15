const $ = (selector) => document.querySelector(selector);
async function api(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(`HTTP ${response.status} · ${data.erro || 'Falha na consulta'}`);
  return data;
}
function show(selector, text, error = false) {
  const node = $(selector);
  node.textContent = text;
  node.classList.toggle('error', error);
  node.classList.toggle('success', !error);
}
async function loadCourses(id = '') {
  const list = $('#courses');
  list.replaceChildren();
  try {
    const data = await api('/api/cursos' + (id ? '?id=' + encodeURIComponent(id) : ''));
    if (!data.cursos.length) { list.textContent = 'Nenhum curso encontrado para esta consulta.'; return; }
    for (const course of data.cursos) {
      const row = document.createElement('article'); row.className = 'course';
      const icon = document.createElement('span'); icon.className = 'course-icon'; icon.textContent = String(course.id).padStart(2, '0');
      const body = document.createElement('div');
      const title = document.createElement('h3'); title.textContent = course.nome;
      const description = document.createElement('p'); description.textContent = course.descricao;
      const arrow = document.createElement('span'); arrow.className = 'arrow'; arrow.textContent = '↗';
      body.append(title, description); row.append(icon, body, arrow); list.append(row);
    }
  } catch (error) { list.textContent = error.message; }
}
async function loadDocument(id) {
  try {
    const doc = await api('/api/documentos/' + encodeURIComponent(id));
    show('#document-result', `${doc.titulo}\nDocumento ${doc.id} · Titular ${doc.dono_id}\n\n${doc.conteudo}`);
  } catch (error) { show('#document-result', error.message, true); }
}
async function refreshAccount() {
  $('#document-list').replaceChildren();
  let user;
  try { user = await api('/api/me'); } catch (_) { user = null; }
  $('#login-form').hidden = Boolean(user);
  $('#logout').hidden = !user;
  $('#account-title').textContent = user ? `Olá, ${user.login}.` : 'Bem-vindo de volta.';
  $('#account-description').textContent = user ? `Perfil: ${user.papel}` : 'Entre para acessar os serviços acadêmicos.';
  show('#document-result', user ? 'Selecione um documento ou informe seu número.' : 'Entre na sua conta para acessar seus documentos.');
  show('#admin-result', 'Os dados serão apresentados após a consulta.');
  if (user) {
    try {
      const data = await api('/api/documentos');
      for (const doc of data.documentos) {
        const button = document.createElement('button'); button.className = 'secondary'; button.textContent = `#${doc.id} · ${doc.titulo}`;
        button.addEventListener('click', () => { $('#document-id').value = doc.id; loadDocument(doc.id); });
        $('#document-list').append(button);
      }
    } catch (error) { show('#document-result', error.message, true); }
  }
}
$('#course-form').addEventListener('submit', (event) => { event.preventDefault(); loadCourses($('#course-id').value.trim()); });
$('#all-courses').addEventListener('click', () => { $('#course-id').value = ''; loadCourses(); });
$('#document-form').addEventListener('submit', (event) => { event.preventDefault(); const id = $('#document-id').value; if (id) loadDocument(id); });
$('#login-form').addEventListener('submit', async (event) => {
  event.preventDefault(); const button = event.currentTarget.querySelector('button'); button.disabled = true;
  try {
    await api('/api/login', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({login: $('#login').value, senha: $('#password').value}) });
    show('#login-result', 'Sessão iniciada.'); await refreshAccount();
  } catch (error) { show('#login-result', error.message, true); }
  finally { button.disabled = false; }
});
$('#logout').addEventListener('click', async () => {
  try { await api('/api/logout', {method: 'POST'}); show('#login-result', 'Sessão encerrada.'); await refreshAccount(); }
  catch (error) { show('#login-result', error.message, true); }
});
$('#admin-button').addEventListener('click', async () => {
  try { const data = await api('/api/admin/resumo'); show('#admin-result', data.perfis.map(p => `${p.nome} · ${p.email}`).join('\n')); }
  catch (error) { show('#admin-result', error.message, true); }
});
loadCourses(); refreshAccount();
