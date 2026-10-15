// Teste de desenvolvimento em navegador headless, com um perfil temporário.
const { chromium } = require('./build/qa/node_modules/playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const evidence = path.join(__dirname, 'evidencias', 'portal', 'interface');
  fs.mkdirSync(evidence, { recursive: true });
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const errors = [];
  try {
    for (const [mode, port] of [['vulneravel', 8081], ['seguro', 8082]]) {
      const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
      const page = await context.newPage();
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(`http://127.0.0.1:${port}`, { waitUntil: 'networkidle' });
      await page.locator('.course').first().waitFor();
      assert.equal(await page.locator('.course').count(), 3);
      await page.screenshot({ path: path.join(evidence, `${mode}-desktop.png`), fullPage: true });
      await page.getByRole('button', { name: 'Entrar no portal' }).click();
      await page.getByText('Olá, ana.', { exact: true }).waitFor();
      await page.getByRole('button', { name: /#101/ }).click();
      await page.locator('#document-result').filter({ hasText: 'LAB_DOCUMENTO_ANA' }).waitFor();
      await page.getByLabel('Número do documento').fill('102');
      await page.getByRole('button', { name: 'Consultar', exact: true }).click();
      await page.locator('#document-result').filter({ hasText: mode === 'vulneravel' ? 'LAB_DOCUMENTO_BRUNO' : 'HTTP 404' }).waitFor();
      await page.getByRole('button', { name: 'Consultar resumo' }).click();
      await page.locator('#admin-result').filter({ hasText: mode === 'vulneravel' ? 'bruno@campus.example' : 'HTTP 403' }).waitFor();
      await page.screenshot({ path: path.join(evidence, `${mode}-acesso.png`), fullPage: true });
      await page.getByRole('button', { name: 'Sair da conta' }).click();
      await page.getByLabel('Usuário', { exact: true }).fill('admin');
      await page.getByRole('button', { name: 'Entrar no portal' }).click();
      await page.getByText('Olá, admin.', { exact: true }).waitFor();
      await page.getByRole('button', { name: 'Consultar resumo' }).click();
      await page.locator('#admin-result').filter({ hasText: 'bruno@campus.example' }).waitFor();
      await page.setViewportSize({ width: 390, height: 844 });
      await page.screenshot({ path: path.join(evidence, `${mode}-mobile.png`), fullPage: true });
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, 'Overflow horizontal no celular');
      await context.close();
    }
    assert.deepEqual(errors, []);
    fs.writeFileSync(path.join(evidence, 'resultado.json'), JSON.stringify({ status: 'aprovado', navegador: 'Edge headless', cenarios: 2, errosJavascript: errors, verificado: ['catalogo', 'login', 'documento proprio', 'IDOR', 'papel administrativo', 'logout', 'administrador autorizado', 'layout mobile'] }, null, 2));
    console.log('Interface: dois cenários aprovados; capturas em ' + evidence);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
