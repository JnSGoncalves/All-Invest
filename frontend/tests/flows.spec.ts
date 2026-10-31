import { test, expect, type Page } from '@playwright/test';

async function register(page: Page) {
  await page.goto('/cadastro');
  await page.getByLabel('Nome completo').fill('Investidora Teste');
  await page.getByLabel('E-mail', { exact: true }).fill(`investidora-${crypto.randomUUID()}@example.com`);
  await page.getByLabel('Senha', { exact: true }).fill('UmaSenhaSegura123');
  await page.getByLabel('Confirmar senha').fill('UmaSenhaSegura123');
  await page.getByRole('button', { name: 'Criar minha conta' }).click();
  await expect(page.getByRole('heading', { name: 'Olá, Investidora' })).toBeVisible();
}

test('integra cadastro, corretora, ação, rendimentos e restauração da sessão com o backend real', async ({ page }) => {
  await register(page);
  await expect(page.getByRole('status').filter({ hasText: 'Cadastro realizado com sucesso.' })).toBeVisible();
  await expect(page.getByText('Nenhuma corretora cadastrada. Cadastre uma corretora para começar.')).toBeVisible();
  await expect(page.getByText('Não há rendimentos. Cadastre um ativo para acompanhar seu rendimento ao longo do tempo.')).toBeVisible();
  const brokers = page.getByRole('region', { name: 'Corretoras', exact: true });
  await brokers.getByRole('button', { name: 'Cadastrar corretora' }).click();
  await expect(brokers.getByRole('alert')).toContainText('Informe o nome');
  await brokers.getByLabel('Nome da corretora').fill('Minha Corretora');
  await brokers.getByRole('button', { name: 'Cadastrar corretora' }).click();
  await expect(brokers.getByRole('status')).toHaveText('Corretora cadastrada com sucesso.');
  await expect(page.getByRole('combobox', { name: 'Corretora', exact: true })).toContainText('Minha Corretora');
  await brokers.getByLabel('Nome da corretora').fill('Minha Corretora');
  await brokers.getByRole('button', { name: 'Cadastrar corretora' }).click();
  await expect(brokers.getByRole('alert')).toContainText('já está vinculada');

  await page.getByLabel('Ticker da ação').fill('PETR4');
  await page.getByLabel('Quantidade', { exact: true }).fill('10');
  await page.getByLabel('Preço por ação').fill('20');
  await page.getByRole('button', { name: 'Registrar compra', exact: true }).click();
  await expect(page.getByRole('cell', { name: 'P PETR4 Petróleo Brasileiro S.A. - Petrobras', exact: true })).toBeVisible();
  const performance = page.getByRole('region', { name: 'Rendimentos por período' });
  await expect(performance.getByRole('cell', { name: 'PETR4', exact: true })).toBeVisible();
  await expect(performance.getByRole('status')).toContainText('185,00');
  await performance.getByRole('combobox', { name: 'Período', exact: true }).selectOption('7');
  await expect(performance.getByRole('status')).toContainText('185,00');
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
  await page.screenshot({ path: '../docs/evidencias/carteira-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(performance.getByRole('combobox', { name: 'Período', exact: true })).toBeVisible();
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
  await page.screenshot({ path: '../docs/evidencias/carteira-mobile.png', fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390);
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Olá, Investidora' })).toBeVisible();
  await expect(brokers.getByRole('listitem')).toHaveText('Minha Corretora');
  await expect(performance.getByRole('status')).toContainText('185,00');
});

test('cadastro rejeita confirmação divergente sem criar a conta', async ({ page }) => {
  let requests = 0;
  page.on('request', request => { if (request.url().endsWith('/api/users')) requests++; });
  await page.goto('/cadastro');
  await page.getByLabel('Nome completo').fill('Teste');
  await page.getByLabel('E-mail', { exact: true }).fill('confirmacao@example.com');
  await page.getByLabel('Senha', { exact: true }).fill('UmaSenhaSegura123');
  await page.getByLabel('Confirmar senha').fill('Diferente123');
  await page.getByRole('button', { name: 'Criar minha conta' }).click();
  await expect(page.getByRole('alert')).toContainText('confirmação de senha');
  expect(requests).toBe(0);
});

test('falha de cotações aparece na área de rendimentos e permite trocar o período', async ({ page }) => {
  await register(page);
  await page.route('**/api/stocks/rendimentos?*', route => route.fulfill({ status: 502, json: { detail: 'Histórico indisponível.' } }));
  const performance = page.getByRole('region', { name: 'Rendimentos por período' });
  await performance.getByRole('combobox', { name: 'Período', exact: true }).selectOption('365');
  await expect(performance.getByRole('alert')).toHaveText('Histórico indisponível.');
  await page.unroute('**/api/stocks/rendimentos?*');
  await performance.getByRole('combobox', { name: 'Período', exact: true }).selectOption('7');
  await expect(performance.getByText('Não há rendimentos.', { exact: false })).toBeVisible();
});
