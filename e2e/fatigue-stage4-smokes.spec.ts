/**
 * Fatigue Meter — Stage 4 entry-session smokes (PLANNING.md §3.5 items 4 + 5).
 *
 * Walks the two owner-required browser-only smokes that block neither Stage 4
 * entry nor calibration but were left open after the 2026-05-04 reconciliation:
 *
 *   - Item 4: 375px viewport — badge wraps, no horizontal overflow, info button
 *     stays tappable (≥44x44 CSS px tap target per WCAG 2.5.5 AAA, treated here
 *     as a soft signal not a gate).
 *   - Item 5: dark-mode contrast across the bands — captures background + text
 *     colors of the rendered badge in dark mode at default and 375px viewports.
 *
 * Captures screenshots and a metrics JSON to artifacts/fatigue-stage4-smokes/
 * so the owner can confirm pass/fail from data instead of opening DevTools.
 *
 * One-shot. Folded into the suite or deleted after Stage 4 entry closes.
 */
import { test, expect, ROUTES, SELECTORS, waitForPageReady } from './fixtures';
import { Page } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const ARTIFACT_DIR = path.join('artifacts', 'fatigue-stage4-smokes');
fs.mkdirSync(ARTIFACT_DIR, { recursive: true });

async function clickDarkModeToggle(page: Page): Promise<void> {
  await page.evaluate(() => {
    const toggle = document.querySelector('#darkModeToggle') as HTMLElement | null;
    if (toggle) toggle.click();
  });
  await page.waitForTimeout(150);
}

async function enableDarkMode(page: Page): Promise<void> {
  await page.goto(ROUTES.HOME);
  await waitForPageReady(page);
  await page.evaluate(() => localStorage.clear());
  await clickDarkModeToggle(page);
  const theme = await page.evaluate(() => document.documentElement.getAttribute('data-theme') || (document.body.classList.contains('dark-mode') ? 'dark' : 'light'));
  expect(['dark', 'true']).toContain(theme);
}

interface Box { x: number; y: number; width: number; height: number }

interface BadgeMetrics {
  url: string;
  viewport: { width: number; height: number };
  colorScheme: 'light' | 'dark';
  badgeBox: Box | null;
  bodyScrollWidth: number;
  bodyClientWidth: number;
  hasHorizontalOverflow: boolean;
  infoButtonBox: Box | null;
  infoButtonMeetsTapTarget: boolean;
  badgeBgColor: string;
  badgeTextColor: string;
  bandLabel: string;
  badgeClass: string;
  screenshotPath: string;
}

const collected: BadgeMetrics[] = [];

async function captureBadge(page: Page, url: string, colorScheme: 'light' | 'dark'): Promise<BadgeMetrics> {
  await page.goto(url);
  await waitForPageReady(page);

  const probed = await page.evaluate(() => {
    const badge = document.querySelector('.fatigue-badge') as HTMLElement | null;
    const infoBtn = document.querySelector('.fatigue-badge__info-btn') as HTMLElement | null;
    const bandEl = document.querySelector('.fatigue-badge__band') as HTMLElement | null;
    const body = document.body;
    const badgeBox = badge ? badge.getBoundingClientRect() : null;
    const infoBox = infoBtn ? infoBtn.getBoundingClientRect() : null;
    const badgeStyle = badge ? getComputedStyle(badge) : null;
    return {
      badgeBox: badgeBox ? { x: badgeBox.x, y: badgeBox.y, width: badgeBox.width, height: badgeBox.height } : null,
      infoBox: infoBox ? { x: infoBox.x, y: infoBox.y, width: infoBox.width, height: infoBox.height } : null,
      bodyScrollWidth: body.scrollWidth,
      bodyClientWidth: body.clientWidth,
      bgColor: badgeStyle ? badgeStyle.backgroundColor : '',
      textColor: badgeStyle ? badgeStyle.color : '',
      bandLabel: bandEl ? (bandEl.textContent || '').trim() : '',
      badgeClass: badge ? badge.className : '',
    };
  });

  const viewport = page.viewportSize() ?? { width: 0, height: 0 };
  const slug = url.replace(/^\//, '').replace(/[^a-z0-9_-]/gi, '_');
  const screenshotName = `${slug}-${viewport.width}w-${colorScheme}.png`;
  const screenshotPath = path.join(ARTIFACT_DIR, screenshotName);
  await page.screenshot({ path: screenshotPath, fullPage: false });

  const metrics: BadgeMetrics = {
    url,
    viewport,
    colorScheme,
    badgeBox: probed.badgeBox,
    bodyScrollWidth: probed.bodyScrollWidth,
    bodyClientWidth: probed.bodyClientWidth,
    hasHorizontalOverflow: probed.bodyScrollWidth > probed.bodyClientWidth + 1,
    infoButtonBox: probed.infoBox,
    infoButtonMeetsTapTarget: probed.infoBox ? probed.infoBox.width >= 44 && probed.infoBox.height >= 44 : false,
    badgeBgColor: probed.bgColor,
    badgeTextColor: probed.textColor,
    bandLabel: probed.bandLabel,
    badgeClass: probed.badgeClass,
    screenshotPath,
  };
  collected.push(metrics);
  return metrics;
}

test.afterAll(() => {
  const summary = JSON.stringify(collected, null, 2);
  fs.writeFileSync(path.join(ARTIFACT_DIR, 'metrics.json'), summary);
  console.log(`\n[fatigue-stage4-smokes] ${collected.length} captures → ${ARTIFACT_DIR}/metrics.json`);
});

test.describe('Fatigue Stage 4 — smoke 4 (375px viewport)', () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test('weekly summary badge fits at 375px (light)', async ({ page }) => {
    const m = await captureBadge(page, ROUTES.WEEKLY_SUMMARY, 'light');
    expect(m.badgeBox, 'badge must render').not.toBeNull();
    expect(m.hasHorizontalOverflow, `no horizontal overflow (scrollWidth=${m.bodyScrollWidth}, clientWidth=${m.bodyClientWidth})`).toBe(false);
    expect(m.infoButtonBox, 'info button must render').not.toBeNull();
  });

  test('session summary badge fits at 375px (light)', async ({ page }) => {
    const m = await captureBadge(page, ROUTES.SESSION_SUMMARY, 'light');
    expect(m.badgeBox).not.toBeNull();
    expect(m.hasHorizontalOverflow, `no horizontal overflow (scrollWidth=${m.bodyScrollWidth}, clientWidth=${m.bodyClientWidth})`).toBe(false);
    expect(m.infoButtonBox).not.toBeNull();
  });
});

test.describe('Fatigue Stage 4 — smoke 5 (dark-mode contrast)', () => {
  test('weekly summary badge in dark mode at default viewport', async ({ page }) => {
    await enableDarkMode(page);
    const m = await captureBadge(page, ROUTES.WEEKLY_SUMMARY, 'dark');
    expect(m.badgeBox).not.toBeNull();
    expect(m.badgeClass).toMatch(/fatigue-badge/);
    expect(m.badgeBgColor, 'badge bg color must be set').not.toBe('');
    expect(m.badgeTextColor, 'badge text color must be set').not.toBe('');
  });

  test('session summary badge in dark mode at default viewport', async ({ page }) => {
    await enableDarkMode(page);
    const m = await captureBadge(page, ROUTES.SESSION_SUMMARY, 'dark');
    expect(m.badgeBox).not.toBeNull();
    expect(m.badgeBgColor).not.toBe('');
    expect(m.badgeTextColor).not.toBe('');
  });

  test('weekly summary badge in dark mode at 375px', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await enableDarkMode(page);
    const m = await captureBadge(page, ROUTES.WEEKLY_SUMMARY, 'dark');
    expect(m.badgeBox).not.toBeNull();
    expect(m.hasHorizontalOverflow).toBe(false);
  });
});
