# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: tests\niche-feed.spec.ts >> Niche Feeds Feature >> should display Niche Filter Chips on the Feed Page
- Location: tests\niche-feed.spec.ts:4:3

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.click: Test timeout of 30000ms exceeded.
Call log:
  - waiting for locator('button').filter({ hasText: 'Fitness' }).first()
    - locator resolved to <button class="shrink-0 rounded-full px-3 py-1 text-xs font-semibold transition-all border bg-muted text-muted-foreground border-border/30 hover:text-foreground">💪 Fitness</button>
  - attempting click action
    - waiting for element to be visible, enabled and stable
  - element was detached from the DOM, retrying

```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - generic [ref=e6]:
    - generic [ref=e7]:
      - heading "Welcome Back" [level=1] [ref=e8]
      - paragraph [ref=e9]: Login to your Trendrop account
    - generic [ref=e10]:
      - generic [ref=e11]:
        - text: Email
        - textbox "Email" [ref=e16]:
          - /placeholder: you@example.com
      - generic [ref=e17]:
        - generic [ref=e18]:
          - generic [ref=e19]: Password
          - button "Forgot password?" [ref=e20]
        - textbox "Password" [ref=e25]:
          - /placeholder: •••••••••
      - button "Login" [ref=e26] [cursor=pointer]
    - generic [ref=e27]:
      - text: Don't have an account?
      - button "Sign up" [ref=e28]
  - region "Notifications alt+T"
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test.describe('Niche Feeds Feature', () => {
  4  |   test('should display Niche Filter Chips on the Feed Page', async ({ page }) => {
  5  |     // We navigate to the vercel deployment where the changes are deployed, or localhost
  6  |     await page.goto('https://trendrop-black.vercel.app/');
  7  |     
  8  |     // Check if the Fitness chip is visible
  9  |     const fitnessChip = page.locator('button', { hasText: 'Fitness' }).first();
  10 |     await expect(fitnessChip).toBeVisible({ timeout: 10000 });
  11 |     
  12 |     // Check if clicking it applies the active class (bg-primary)
> 13 |     await fitnessChip.click();
     |                       ^ Error: locator.click: Test timeout of 30000ms exceeded.
  14 |     await expect(fitnessChip).toHaveClass(/bg-primary/);
  15 |   });
  16 | });
  17 | 
```