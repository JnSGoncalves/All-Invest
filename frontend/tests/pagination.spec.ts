import { test, expect } from '@playwright/test';

test('navega pelas posições mantendo o resumo da carteira', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('allinvest.refresh_token', 'test-refresh'));
  await page.route('**/api/v1/auth/refresh', route => route.fulfill({ json: {
    access_token: 'test-access', refresh_token: 'test-refresh', expires_in: 3600,
    user: { user_id: 1, name: 'Investidora Teste', email: 'teste@example.com' },
  } }));
  // A lista vem ordenada por valor aplicado: PETR4 abre a página 1 e VALE3 fica sozinha na 2.
  const tickers = ['PETR4', ...Array.from({ length: 9 }, (_, index) => `ATIV${index + 1}`), 'VALE3'];
  await page.route('**/api/stocks/carteira', route => route.fulfill({ json: tickers.map((stock_name, index) => ({
    stock_name, company_name: 'Empresa', stock_quantity: 10, preco_medio: 30 - index, portfolio_id: null, portfolio_name: null,
  })) }));
  await page.goto('/');
  await expect(page.getByRole('cell', { name: 'PE PETR4 Empresa', exact: true })).toBeVisible();
  const summary = page.getByRole('region', { name: 'Resumo da carteira' });
  const before = await summary.innerText();
  await expect(page.getByRole('button', { name: 'Anterior' })).toBeDisabled();
  await page.getByRole('button', { name: 'Próxima' }).click();
  await expect(page.getByRole('cell', { name: 'VA VALE3 Empresa', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Próxima' })).toBeDisabled();
  expect(await summary.innerText()).toBe(before);
  await page.getByRole('button', { name: 'Anterior' }).click();
  await expect(page.getByRole('cell', { name: 'PE PETR4 Empresa', exact: true })).toBeVisible();
});
