# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: tests\admin_panel.spec.ts >> Admin Panel Verification >> admin login, verify users, upgrade free to pro
- Location: tests\admin_panel.spec.ts:11:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('text=Pro, badge')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('text=Pro, badge')

```

```yaml
- text: trendr p
- button "Notifications"
- button "Toggle theme": ◐ dark
- button "Profile": f
- paragraph: 0 active trends tracked
- button "Rising"
- button "Emerging"
- button "Workspace"
- button "Peaked"
- button "Expired"
- textbox "Search song or artist..."
- button "All"
- button "💪 Fitness"
- button "🍜 Food"
- button "😂 Comedy"
- button "👗 Fashion"
- button "💼 Business"
- button "✈️ Travel"
- button "💄 Beauty"
- navigation "Main navigation":
  - list:
    - listitem:
      - link "Trends":
        - /url: /
    - listitem:
      - link "Dashboard":
        - /url: /dashboard
    - listitem:
      - link "Generate":
        - /url: /generate
    - listitem:
      - link "Ideas":
        - /url: /ideas
    - listitem:
      - link "Settings":
        - /url: /settings
- region "Notifications alt+T":
  - list:
    - listitem:
      - img
      - text: Login successful!
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test.describe('Admin Panel Verification', () => {
  4  |   const adminEmail = 'new_admin_playwright@trendrop.internal';
  5  |   const adminPassword = 'AdminTest123!';
  6  |   const freeUserEmail = 'free_test_playwright@trendrop.internal';
  7  | 
  8  |   // Note: For this to work fully without setup scripts, the admin and free user
  9  |   // should ideally be seeded in the DB prior to running the test.
  10 | 
  11 |   test('admin login, verify users, upgrade free to pro', async ({ page, request }) => {
  12 |     // 1. Admin Login
  13 |     await page.goto('https://trendrop-black.vercel.app/admin/login');
  14 |     await page.fill('input[type="email"]', adminEmail);
  15 |     await page.fill('input[type="password"]', adminPassword);
  16 |     await page.click('button[type="submit"]');
  17 | 
  18 |     // Verify navigation to dashboard
  19 |     await expect(page).toHaveURL(/.*\/admin.*/);
  20 | 
  21 |     // 2. See if users are shown
  22 |     // Verify the user management heading is visible
  23 |     await expect(page.locator('h1:has-text("User Management")')).toBeVisible({ timeout: 10000 });
  24 | 
  25 |     // 3. Upgrade free account to pro
  26 |     // Search for the free user
  27 |     const searchInput = page.locator('input[placeholder*="Search"]');
  28 |     await searchInput.fill(freeUserEmail);
  29 |     
  30 |     // Find the user card
  31 |     const userCard = page.locator(`h3:has-text("${freeUserEmail}")`).locator('..').locator('..').locator('..');
  32 |     await expect(userCard).toBeVisible();
  33 | 
  34 |     // Verify it's a free account currently (inside the card stats)
  35 |     await expect(userCard).toContainText(/free/i);
  36 | 
  37 |     // Click 'Details' to open the modal
  38 |     await userCard.locator('button:has-text("Details")').click();
  39 | 
  40 |     // Verify modal opens
  41 |     const modal = page.locator('h2:has-text("User Details")').locator('..').locator('..');
  42 |     await expect(modal).toBeVisible();
  43 | 
  44 |     // Click to upgrade to Pro
  45 |     await modal.locator('button:has-text("Pro")').click();
  46 | 
  47 |     // Close the modal
  48 |     await modal.locator('button:has-text("✕")').click();
  49 | 
  50 |     // Wait for the modal to disappear
  51 |     await expect(modal).not.toBeVisible();
  52 | 
  53 |     // 4. Check if the free account shows pro features (Login as the free user)
  54 |     // Clear cookies/storage to simulate fresh login
  55 |     await page.context().clearCookies();
  56 |     await page.goto('https://trendrop-black.vercel.app/login');
  57 |     await page.fill('input[type="email"]', freeUserEmail);
  58 |     await page.fill('input[type="password"]', 'TestUser123!');
  59 |     await page.click('button[type="submit"]');
  60 | 
  61 |     // Check pro features (e.g., unlimited searches, pro badge)
> 62 |     await expect(page.locator('text=Pro, badge')).toBeVisible();
     |                                                   ^ Error: expect(locator).toBeVisible() failed
  63 |   });
  64 | });
  65 | 
```