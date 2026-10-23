import { test, expect } from '@playwright/test';

/**
 * E2E smoke (updated Milestone 14 for the real cookie-auth UX from M12).
 *
 * STATE-CHANGING BEHAVIOR COVERED: one intentional bad-credential login
 * attempt in the last test (401 + generic message). No credentials exist in
 * this file — there is no public registration by design, so anonymous E2E
 * cannot access protected tabs; those verifications stay covered by the
 * backend route tests + manual staging verification.
 *
 * NOTE: with the pp13 disposable stack up on :8000, the login-failure test
 * writes a real audit event (login_failure) — by design in M14.
 */

test.describe('PHANTOM PHOENIX E2E Smoke Tests', () => {
  test('Landing page loads and dashboard is gated for guests', async ({ page }) => {
    await page.goto('/');

    // Check hero headline on landing page
    await expect(page.locator('h2', { hasText: 'Digital Media Authenticity & AI Forensic Intelligence' })).toBeVisible();

    // Click Investigator Dashboard CTA — unauthenticated users are routed to sign-in
    await page.click('text=Investigator Dashboard');
    await expect(page).toHaveURL(/#login/);
    await expect(page.locator('h2', { hasText: 'Investigator Sign-In' })).toBeVisible();
  });

  test('Hash routing back/forward works for public tabs', async ({ page }) => {
    await page.goto('/#login');
    await expect(page.locator('h2', { hasText: 'Investigator Sign-In' })).toBeVisible();

    await page.goto('/#landing');
    await expect(page.locator('h2', { hasText: 'Digital Media Authenticity & AI Forensic Intelligence' })).toBeVisible();

    // Test browser back/forward
    await page.goBack();
    await expect(page).toHaveURL(/#login/);

    await page.goForward();
    await expect(page).toHaveURL(/#landing/);
  });

  test('Protected direct links redirect guests to sign-in', async ({ page }) => {
    await page.goto('/#history');
    await expect(page).toHaveURL(/#login/);
    await expect(page.locator('h2', { hasText: 'Investigator Sign-In' })).toBeVisible();
  });

  test('Invalid sign-in shows generic failure message (no account-name disclosure)', async ({ page }) => {
    await page.goto('/#login');
    await expect(page.locator('h2', { hasText: 'Investigator Sign-In' })).toBeVisible();

    await page.fill('#login-username', 'no_such_user_e2e');
    await page.fill('input[name="password"]', 'definitely-not-a-password-1');
    await page.locator('form[aria-label="Investigator login"] button[type="submit"]').click();

    await expect(
      page.locator('text=Invalid username or password.')
    ).toBeVisible({ timeout: 10000 });
    // generic failure message must not echo the attempted username
    // (username field keeps its value by design — only password is cleared)
    const pageText = await page.locator('body').textContent();
    expect(pageText).not.toContain('no_such_user_e2e');
  });
});
