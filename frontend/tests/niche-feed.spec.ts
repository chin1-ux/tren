import { test, expect } from '@playwright/test';

test.describe('Niche Feeds Feature', () => {
  test('should display Niche Filter Chips on the Feed Page', async ({ page }) => {
    // We navigate to the vercel deployment where the changes are deployed, or localhost
    await page.goto('https://trendrop-black.vercel.app/');
    
    // Check if the Fitness chip is visible
    const fitnessChip = page.locator('button', { hasText: 'Fitness' }).first();
    await expect(fitnessChip).toBeVisible({ timeout: 10000 });
    
    // Check if clicking it applies the active class (bg-primary)
    await fitnessChip.click();
    await expect(fitnessChip).toHaveClass(/bg-primary/);
  });
});
