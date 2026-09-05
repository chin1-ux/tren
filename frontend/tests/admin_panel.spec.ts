import { test, expect } from '@playwright/test';

test.describe('Admin Panel Verification', () => {
  const adminEmail = 'new_admin_playwright@trendrop.internal';
  const adminPassword = 'AdminTest123!';
  const freeUserEmail = 'free_test_playwright@trendrop.internal';

  // Note: For this to work fully without setup scripts, the admin and free user
  // should ideally be seeded in the DB prior to running the test.

  test('admin login, verify users, upgrade free to pro', async ({ page, request }) => {
    // 1. Admin Login
    await page.goto('https://trendrop-black.vercel.app/admin/login');
    await page.fill('input[type="email"]', adminEmail);
    await page.fill('input[type="password"]', adminPassword);
    await page.click('button[type="submit"]');

    // Verify navigation to dashboard
    await expect(page).toHaveURL(/.*\/admin.*/);

    // 2. See if users are shown
    // Verify the user management heading is visible
    await expect(page.locator('h1:has-text("User Management")')).toBeVisible({ timeout: 10000 });

    // 3. Upgrade free account to pro
    // Search for the free user
    const searchInput = page.locator('input[placeholder*="Search"]');
    await searchInput.fill(freeUserEmail);
    
    // Find the user card
    const userCard = page.locator(`h3:has-text("${freeUserEmail}")`).locator('..').locator('..').locator('..');
    await expect(userCard).toBeVisible();

    // Verify it's a free account currently (inside the card stats)
    await expect(userCard).toContainText(/free/i);

    // Click 'Details' to open the modal
    await userCard.locator('button:has-text("Details")').click();

    // Verify modal opens
    const modal = page.locator('h2:has-text("User Details")').locator('..').locator('..');
    await expect(modal).toBeVisible();

    // Click to upgrade to Pro
    await modal.locator('button:has-text("Pro")').click();

    // Close the modal
    await modal.locator('button:has-text("✕")').click();

    // Wait for the modal to disappear
    await expect(modal).not.toBeVisible();

    // 4. Check if the free account shows pro features (Login as the free user)
    // Clear cookies/storage to simulate fresh login
    await page.context().clearCookies();
    await page.goto('https://trendrop-black.vercel.app/login');
    await page.fill('input[type="email"]', freeUserEmail);
    await page.fill('input[type="password"]', 'TestUser123!');
    await page.click('button[type="submit"]');

    // Wait for login to complete and navigate to dashboard
    await expect(page).toHaveURL(/.*\/dashboard|.*\//);
    
    // Optionally go to settings to check the plan
    await page.goto('https://trendrop-black.vercel.app/settings');
    // We expect the word 'Pro' to appear in the settings page now!
    await expect(page.locator('text=Pro').first()).toBeVisible({ timeout: 10000 });
  });
});
