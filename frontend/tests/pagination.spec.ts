import { test, expect } from '@playwright/test';

test('navega pelas posições mantendo o resumo da carteira', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('allinvest.refresh_token', 'test-refresh'));
  await page.route('**/api/v1/auth/refresh', route => route.fulfill({ json: {
    access_token: 'test-access', refresh_token: 'test-refresh', expires_in: 3600,
    user: { user_id: 1, name: 'Investidora Teste', email: 'teste@example.com' },
  } }));
  await page.route('**/api/stocks/carteira/paginada?*', route => {
    const current = Number(new URL(route.request().url()).searchParams.get('page'));
    return route.fulfill({ json: {
      results: [{ stock_name: current === 1 ? 'PETR4' : 'VALE3', company_name: 'Empresa', stock_quantity: 10, preco_medio: 20 }],
      page: current, total_pages: 2, total_items: 11, total_quantity: 110, total_invested: 2200,
    } });
  });
  await page.goto('/');
  await expect(page.getByRole('cell', { name: 'P PETR4 Empresa', exact: true })).toBeVisible();
  const summary = page.getByRole('region', { name: 'Resumo da carteira' });
  const before = await summary.innerText();
  await expect(page.getByRole('button', { name: 'Anterior' })).toBeDisabled();
  await page.getByRole('button', { name: 'Próxima' }).click();
  await expect(page.getByRole('cell', { name: 'V VALE3 Empresa', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Próxima' })).toBeDisabled();
  expect(await summary.innerText()).toBe(before);
  await page.getByRole('button', { name: 'Anterior' }).click();
  await expect(page.getByRole('cell', { name: 'P PETR4 Empresa', exact: true })).toBeVisible();
});
