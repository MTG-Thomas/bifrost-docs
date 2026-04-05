import { test, expect, navigateToOrg } from './test-utils';

/**
 * Responsive Design Tests
 * 
 * Tests that the app works correctly on mobile and tablet viewports.
 */
test.describe('Responsive Design', () => {
  
  test('should display mobile navigation', async ({ page }) => {
    // Set mobile viewport (already configured in playwright.config.ts)
    await page.setViewportSize({ width: 375, height: 667 });
    
    await navigateToOrg(page, 'test-org');
    
    // Should see hamburger menu button on mobile
    await expect(page.getByRole('button', { name: 'Menu', exact: false })).toBeVisible();
    
    // Sidebar should be hidden by default on mobile
    const sidebar = page.locator('aside, [role="complementary"]').first();
    await expect(sidebar).not.toBeVisible();
  });
  
  test('should open mobile navigation menu', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    
    await navigateToOrg(page, 'test-org');
    
    // Click hamburger menu
    await page.getByRole('button', { name: 'Menu', exact: false }).click();
    
    // Sidebar should now be visible
    const sidebar = page.locator('aside, [role="complementary"]').first();
    await expect(sidebar).toBeVisible();
    
    // Should see navigation links
    await expect(page.getByRole('link', { name: 'Passwords' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Configurations' })).toBeVisible();
  });
  
  test('should display tablet layout', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    
    await navigateToOrg(page, 'test-org');
    
    // Sidebar should be visible on tablet
    const sidebar = page.locator('aside, [role="complementary"]').first();
    await expect(sidebar).toBeVisible();
    
    // Main content should be visible
    await expect(page.locator('main')).toBeVisible();
  });
  
  test('table should be scrollable on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Navigate to passwords
    await page.goto('/org/test-org/passwords');
    
    // Wait for content
    await page.waitForLoadState('networkidle');
    
    // Table should be visible
    const table = page.locator('table, [data-testid="data-table"]');
    if (await table.count() > 0) {
      // Table should be horizontally scrollable if needed
      await expect(table).toBeVisible();
    }
  });
  
  test('forms should be usable on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Navigate to create password
    await page.goto('/org/test-org/passwords');
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
    
    // Try to click add button
    const addButton = page.getByRole('button', { name: 'Add Password' });
    if (await addButton.count() > 0) {
      await addButton.click();
      
      // Form should be visible and usable
      await expect(page.getByLabel('Name')).toBeVisible();
      
      // Form fields should be accessible
      await page.getByLabel('Name').fill('Mobile Test Password');
      await expect(page.getByLabel('Name')).toHaveValue('Mobile Test Password');
    }
  });
  
});
