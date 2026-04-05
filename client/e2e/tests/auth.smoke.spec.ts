import { test, expect, performLogin } from './test-utils';

/**
 * Smoke Test Suite: Authentication
 * 
 * Tests basic login/logout functionality across browsers.
 */
test.describe('Authentication', () => {
  
  test('should display login page', async ({ page }) => {
    await page.goto('/login');
    
    // Verify page title and form elements
    await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible();
    await expect(page.getByLabel('Email')).toBeVisible();
    await expect(page.getByLabel('Password')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible();
  });
  
  test('should login with valid credentials', async ({ page }) => {
    // Use the test utility to login
    await performLogin(page, 'test@example.com', 'TestPassword123!');
    
    // After login, should be on org selector or dashboard
    const currentUrl = page.url();
    expect(currentUrl).toMatch(/\/(org\/[^/]+|organizations)/);
  });
  
  test('should show error with invalid credentials', async ({ page }) => {
    await page.goto('/login');
    
    // Fill in wrong credentials
    await page.getByLabel('Email').fill('wrong@example.com');
    await page.getByLabel('Password').fill('wrongpassword');
    
    // Submit form
    await page.getByRole('button', { name: 'Sign in' }).click();
    
    // Should show error message
    await expect(page.getByText('Invalid email or password')).toBeVisible();
    
    // Should still be on login page
    expect(page.url()).toContain('/login');
  });
  
  test('should navigate to register page', async ({ page }) => {
    await page.goto('/login');
    
    // Click register link
    await page.getByRole('link', { name: 'Create an account' }).click();
    
    // Should be on register page
    await expect(page).toHaveURL('/register');
    await expect(page.getByRole('heading', { name: 'Create account' })).toBeVisible();
  });
  
});
