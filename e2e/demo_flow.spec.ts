import { test, expect } from '@playwright/test';

test.describe('Phase 10 E2E Demo Story (§10 Walkthrough)', () => {
  test('executes end-to-end demo path click by click with no manual intervention', async ({ page }) => {
    // 1. Visit Login Page
    await page.goto('/login');
    await expect(page.getByText(/SYNTHETIC DATA ONLY/i)).toBeVisible();
    await expect(page.getByText(/AeroPulse Cockpit/i)).toBeVisible();

    // 2. Perform Quick Login as Planner
    const plannerButton = page.getByRole('button', { name: /Planner/i });
    await expect(plannerButton).toBeVisible();
    await plannerButton.click();

    // 3. Step 1: Fleet Dashboard
    await page.waitForURL('**/dashboard');
    await expect(page.getByText(/Fleet Operational Cockpit/i)).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/SYNTHETIC DATA/i).first()).toBeVisible();

    // Verify key KPIs appear on the dashboard
    await expect(page.getByText(/Availability/i).first()).toBeVisible();

    // 4. Step 2: Spot the issue — Navigate to Aircraft Detail & Twin
    const aircraftNav = page.getByRole('link', { name: /Aircraft Detail & Twin/i });
    await aircraftNav.click();
    await page.waitForURL('**/aircraft**');
    await expect(page.getByText(/Airframe/i).first()).toBeVisible({ timeout: 10_000 });

    // 5. Step 3: Sensor Trends & Anomaly — Navigate to Component Health
    const compNav = page.getByRole('link', { name: /Component Health/i });
    await compNav.click();
    await page.waitForURL('**/components**');
    await expect(page.getByText(/Component Health/i).first()).toBeVisible({ timeout: 10_000 });

    // 6. Step 4: Predictive Queue — Advisories
    const queueNav = page.getByRole('link', { name: /Predictive Queue/i });
    await queueNav.click();
    await page.waitForURL('**/advisories');
    await expect(page.getByText(/Predictive/i).first()).toBeVisible({ timeout: 10_000 });

    // 7. Step 5: Planning & Work Orders
    const planningNav = page.getByRole('link', { name: /Planning & Work Orders/i });
    await planningNav.click();
    await page.waitForURL('**/planning');
    await expect(page.getByText(/Planning/i).first()).toBeVisible({ timeout: 10_000 });

    // 8. Step 6: Spares Inventory
    const sparesNav = page.getByRole('link', { name: /Spares Inventory/i });
    await sparesNav.click();
    await page.waitForURL('**/spares');
    await expect(page.getByText(/Spares/i).first()).toBeVisible({ timeout: 10_000 });

    // 9. Step 7: Scenario Simulator
    const simNav = page.getByRole('link', { name: /Scenario Simulator/i });
    await simNav.click();
    await page.waitForURL('**/scenarios');
    await expect(page.getByText(/Simulator/i).first()).toBeVisible({ timeout: 10_000 });
  });
});
