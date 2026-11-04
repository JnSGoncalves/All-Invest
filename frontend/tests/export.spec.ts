import { test, expect, type Page } from '@playwright/test';

const position = { stock_name: 'PETR4', company_name: 'Petrobras', stock_quantity: 10, preco_medio: 30, portfolio_id: 7, portfolio_name: 'Dividendos' };

async function openDashboard(page: Page) {
  await page.addInitScript(() => localStorage.setItem('allinvest.refresh_token', 'test-refresh'));
  await page.route('**/api/v1/auth/refresh', route => route.fulfill({ json: {
    access_token: 'test-access', refresh_token: 'test-refresh', expires_in: 3600,
    user: { user_id: 1, name: 'Investidora Teste', email: 'teste@example.com' },
  } }));
  await page.route('**/api/stocks/carteira', route => route.fulfill({ json: [position] }));
  await page.route('**/api/portfolios', route => route.fulfill({ json: [
    { portfolio_id: 7, portfolio_name: 'Dividendos', description: null, created_at: '2026-01-01T00:00:00Z' },
  ] }));
  await page.goto('/');
  await expect(page.getByRole('cell', { name: 'PE PETR4 Dividendos Petrobras' })).toBeVisible();
}

test('baixa a planilha de todas as posições', async ({ page }) => {
  await openDashboard(page);
  const requests: string[] = [];
  await page.route('**/api/reports/export*', route => {
    requests.push(route.request().url());
    return route.fulfill({ body: 'planilha', contentType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
  });

  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Exportar Excel' }).click();

  expect((await download).suggestedFilename()).toMatch(/^all-invest-carteira-\d{4}-\d{2}-\d{2}\.xlsx$/);
  expect(new URL(requests[0]).search).toBe('');
  await expect(page.getByText('Todas as suas posições foram exportadas para Excel.')).toBeVisible();
});

test('exporta somente a carteira filtrada', async ({ page }) => {
  await openDashboard(page);
  const requests: string[] = [];
  await page.route('**/api/reports/export*', route => {
    requests.push(route.request().url());
    return route.fulfill({ body: 'planilha' });
  });

  await page.getByRole('tab', { name: 'Dividendos' }).click();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Exportar Excel' }).click();
  await download;

  expect(new URL(requests[0]).search).toBe('?portfolio_id=7');
  await expect(page.getByText('Carteira “Dividendos” exportada para Excel.')).toBeVisible();
});

test('informa quando a planilha não pode ser gerada', async ({ page }) => {
  await openDashboard(page);
  await page.route('**/api/reports/export*', route => route.fulfill({ status: 404, json: { detail: 'Carteira não encontrada.' } }));

  await page.getByRole('button', { name: 'Exportar Excel' }).click();

  await expect(page.getByText('Não foi possível gerar a planilha')).toBeVisible();
  await expect(page.getByText('Carteira não encontrada.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Exportar Excel' })).toBeEnabled();
});
