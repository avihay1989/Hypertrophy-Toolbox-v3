import type { Locator, Page } from '@playwright/test';

export type VisualTheme = 'light' | 'dark';

export interface VisualDeterminismOptions {
  theme: VisualTheme;
}

export async function installDeterminism(
  page: Page,
  options: VisualDeterminismOptions,
): Promise<void> {
  await page.addInitScript((theme) => {
    const FIXED = new Date('2026-04-18T09:00:00Z').valueOf();
    const NativeDate = Date;

    // Keep no-argument Date construction and Date.now() stable for screenshots.
    // @ts-ignore - this class intentionally shadows the browser Date constructor.
    globalThis.Date = class extends NativeDate {
      constructor(...args: any[]) {
        // Cast to a tuple so the spread satisfies tsc (TS2556); the Date copy
        // shim forwards all original args unchanged at runtime.
        super(...((args.length ? args : [FIXED]) as [number]));
      }

      static now() {
        return FIXED;
      }
    };

    localStorage.clear();
    localStorage.setItem('darkMode', theme === 'dark' ? 'true' : 'false');
    document.documentElement?.setAttribute('data-theme', theme);
  }, options.theme);
}

export async function prepareForScreenshot(page: Page): Promise<void> {
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle');

  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation-delay: 0s !important;
        animation-duration: 0s !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0s !important;
        transition-delay: 0s !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
      }

      html { scroll-behavior: auto !important; }
      html {
        --visual-surface-0: #eef1f6;
        --visual-surface-1: #f7f9fc;
      }
      html[data-theme='dark'] {
        --visual-surface-0: #090c16;
        --visual-surface-1: #0d101d;
      }
      html[data-theme] body,
      body {
        background: var(--visual-surface-0) !important;
        background-attachment: scroll !important;
      }

      html[data-theme='dark'] [data-visual-surface][data-visual-surface] {
        background: var(--visual-surface-1) !important;
        background-image: none !important;
        border-color: #273145 !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        text-shadow: none !important;
      }
      html[data-theme='dark'] [data-page="workout-plan"] [data-visual-header]::before {
        background: transparent !important;
      }
      html[data-theme='dark'] [data-page="workout-plan"] [data-visual-accent] {
        background: #4f8cff !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        transform: none !important;
        transition: none !important;
      }

      input, textarea { caret-color: transparent !important; }
      select {
        appearance: none !important;
        -webkit-appearance: none !important;
        background-image: none !important;
      }
      [data-visual-control],
      input,
      textarea,
      select,
      input[type="number"] {
        border-radius: 0 !important;
        box-shadow: none !important;
        text-shadow: none !important;
      }
      [data-testid="navbar"] a::before,
      [data-testid="navbar"] button::before {
        background-color: transparent !important;
        border-radius: 0 !important;
        transform: none !important;
        transition: none !important;
      }
      [data-visual-dropdown-toggle]::after {
        border-color: transparent !important;
      }
      [data-visual-icon] {
        visibility: hidden !important;
      }
      [data-visual-scale-control] {
        background: transparent !important;
        border-color: transparent !important;
        color: transparent !important;
      }
      input[type="number"]::-webkit-outer-spin-button,
      input[type="number"]::-webkit-inner-spin-button {
        -webkit-appearance: none !important;
        margin: 0 !important;
      }
      ::-webkit-scrollbar { display: none; }
    `,
  });

  await page.evaluate(async () => {
    document
      .querySelectorAll<HTMLElement>(
        '[data-visual-control], input, textarea, select',
      )
      .forEach((element) => {
        element.style.setProperty('border-radius', '0', 'important');
        element.style.setProperty('box-shadow', 'none', 'important');
        element.style.setProperty('text-shadow', 'none', 'important');
      });

    await document.fonts.ready;
    window.scrollTo(0, 0);
  });
}

export function visualScreenshotOptions(page: Page): {
  animations: 'disabled';
  caret: 'hide';
  fullPage: true;
  mask: Locator[];
  maxDiffPixels: number;
  threshold: 0;
} {
  return {
    fullPage: true,
    animations: 'disabled',
    caret: 'hide',
    mask: [
      page.locator('#auto-backup-banner'),
      page.locator('.timestamp, [data-volatile]'),
      page.locator('.toast-container'),
      page.locator('img[src$=".gif"]'),
    ],
    maxDiffPixels: 800,
    threshold: 0,
  };
}

/**
 * Screenshot options for element/locator-scoped shots (e.g. a single table),
 * sharing the same animation/caret/tolerance discipline as the full-page
 * baselines but without `fullPage` (invalid for a locator screenshot).
 */
export function elementScreenshotOptions(): {
  animations: 'disabled';
  caret: 'hide';
  maxDiffPixels: number;
  threshold: 0;
} {
  return {
    animations: 'disabled',
    caret: 'hide',
    maxDiffPixels: 800,
    threshold: 0,
  };
}
