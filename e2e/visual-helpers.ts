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
        super(...(args.length ? args : [FIXED]));
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
      }

      html { scroll-behavior: auto !important; }

      input, textarea { caret-color: transparent !important; }
      select,
      .form-select {
        appearance: none !important;
        -webkit-appearance: none !important;
        background-image: none !important;
      }
      .wpdd-button,
      .form-control,
      .form-select,
      select,
      input[type="number"] {
        border-radius: 0 !important;
        box-shadow: none !important;
        text-shadow: none !important;
      }
      #workout[data-page="workout-plan"] .wpdd-button,
      #workout[data-page="workout-plan"] .filter-dropdown,
      #workout[data-page="workout-plan"] .form-select,
      #workout[data-page="workout-plan"] .uniform-input,
      #workout[data-page="workout-plan"] input[type="number"] {
        border-radius: 0 !important;
        box-shadow: none !important;
        text-shadow: none !important;
      }
      #navbar .nav-link,
      #navbar button,
      #navbar .scale-control-compact,
      #navbar .scale-btn-compact,
      #navbar .scale-indicator {
        border-radius: 0 !important;
        box-shadow: none !important;
        text-shadow: none !important;
      }
      #navbar .scale-btn-compact,
      #navbar .scale-indicator {
        background: transparent !important;
        border-color: transparent !important;
        color: transparent !important;
      }
      #navbar .nav-link::before,
      #navbar .navbar-brand::before,
      #navbar #darkModeToggle::before,
      #navbar #muscleModeToggle::before {
        background-color: transparent !important;
        border-radius: 0 !important;
        transform: none !important;
        transition: none !important;
      }
      #navbar .nav-link.active {
        border-color: transparent !important;
        box-shadow: none !important;
      }
      #navbar #darkModeToggle,
      #navbar #muscleModeToggle,
      #navbar .nav-signature-link {
        border-radius: 0 !important;
      }
      #navbar #darkModeToggle i,
      #navbar #muscleModeToggle i,
      #navbar .signature-icon {
        visibility: hidden !important;
      }
      input[type="number"]::-webkit-outer-spin-button,
      input[type="number"]::-webkit-inner-spin-button {
        -webkit-appearance: none !important;
        margin: 0 !important;
      }
      .wpdd-caret { visibility: hidden !important; }
      ::-webkit-scrollbar { display: none; }
    `,
  });

  await page.evaluate(async () => {
    document
      .querySelectorAll<HTMLElement>(
        '.wpdd-button, .form-control, .form-select, input[type="number"], #navbar .scale-btn-compact, #navbar .scale-indicator',
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
  maxDiffPixels: 0;
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
    maxDiffPixels: 0,
    threshold: 0,
  };
}
