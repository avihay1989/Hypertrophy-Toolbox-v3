/**
 * Bare `.scale-btn` family census and certification harness.
 *
 * WP4.4-d1 deleted a superseded scale/menu generation from `static/css/a11y.css`
 * but deliberately EXCLUDED the eleven bare `.scale-btn` occurrences, because
 * its static pass had treated the `querySelectorAll('.scale-btn[data-scale]')`
 * calls in `static/js/accessibility.js` as proof of reachability -- the exact
 * "a JavaScript query alone does not prove reachability" trap. d1 recorded the
 * gap and required "its own census and its own packet" (d1 evidence 3a). This
 * is that packet's instrument.
 *
 * What it produces, in the order the evidence has to be believed:
 *
 *   1. oracle validity      known-live controls that MUST report live, a
 *                           known-dead control that MUST report dead, and a
 *                           same-CSS control that MUST report zero differing
 *                           records. A control failure invalidates the run.
 *   2. natural census       full-selector `querySelectorAll` counts taken
 *                           BEFORE any synthetic is injected, across routes x
 *                           themes x widths x data-scale levels, plus print and
 *                           reduced motion.
 *   3. certification        a synthetic bearer plus a control that fails the
 *                           selector by exactly ONE compound, per member, with
 *                           a sentinel derived from that member's OWN
 *                           declarations, asserted to take effect AND revert.
 *   4. declaration owner    CDP `CSS.getMatchedStylesForNode`, which is the
 *                           only oracle that separates members whose computed
 *                           values collide (member 8 vs member 1) or whose
 *                           declared property is stolen by a later `!important`
 *                           rule (member 3).
 *   5. rest state           every element's computed paint values, so the
 *                           deletion can be shown neutral for OTHER elements.
 *
 * Three member-specific hazards are handled explicitly, because each would
 * otherwise manufacture a false verdict:
 *
 *   member 3  `.scale-btn:focus` declares `outline` and `outline-offset`.
 *             `a11y.css` later declares `*:focus { outline: none !important }`,
 *             so `outline` can NEVER compute from this rule. Only
 *             `outline-offset` is observable, and only in a `:focus` that is
 *             NOT `:focus-visible`. Unobservable is not unreachable.
 *   member 8  `.scale-btn[data-scale="3"] { font-size: 0.75rem }` is
 *             byte-identical to member 1's `font-size`. Computed style cannot
 *             separate them; CDP source range can.
 *   member 11 lives inside `@media (max-width: 991.98px)` and is invisible at
 *             any wider viewport -- d1's defect #1, which "would have
 *             manufactured false deadness".
 *
 * Generated output goes to artifacts/ (gitignored).
 *
 * usage:
 *   node scripts/css_audit/scale_btn_census.mjs --out artifacts/scale_btn/before
 *   node scripts/css_audit/scale_btn_census.mjs --diff artifacts/scale_btn/before artifacts/scale_btn/after
 */
import { chromium } from '@playwright/test';
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync, readFileSync, rmSync } from 'node:fs';
import { resolve } from 'node:path';
import { connect } from 'node:net';

const PORT = Number(process.env.HT_PROBE_PORT ?? 5247);
const BASE_URL = `http://127.0.0.1:${PORT}`;

const ROUTES = [
  { name: 'welcome', path: '/' },
  { name: 'workout-plan', path: '/workout_plan' },
  { name: 'workout-log', path: '/workout_log' },
  { name: 'weekly-summary', path: '/weekly_summary' },
  { name: 'session-summary', path: '/session_summary' },
  { name: 'progression', path: '/progression' },
  { name: 'body-composition', path: '/body_composition' },
  { name: 'volume-splitter', path: '/volume_splitter' },
  { name: 'user-profile', path: '/user_profile' },
  { name: 'backup', path: '/backup' },
  { name: 'fatigue', path: '/fatigue' },
];

const THEMES = ['light', 'dark'];

// Bracket a11y.css's two width breakpoints. `max-width: 991.98px` is DECIMAL:
// 991 is the largest integer viewport that satisfies it and 992 the smallest
// that does not. Probing a media-gated rule only at widths its block cannot
// apply to is d1 defect #1 and manufactures false deadness.
const WIDTHS = [375, 576, 768, 769, 820, 991, 992, 1200, 1440, 1920];

// accessibility.js:79 -- the exact ladder `applyScale` writes.
const ZOOM_BY_SCALE = { 1: '0.75', 2: '0.8', 3: '0.85', 4: '0.9', 5: '0.95', 6: '1', 7: '1.1', 8: '1.2' };
const SCALES = [1, 2, 3, 4, 5, 6, 7, 8];

const MEDIA_MAX = 991.98;

/**
 * The eleven candidates, each with a sentinel derived from its OWN
 * declarations and unique within the family.
 *
 * `needsWidth` marks the member that only exists below the breakpoint.
 * `computedBlind` marks the member no computed-style read can separate from
 * another member -- it certifies by CDP source range alone, and saying so is
 * the point rather than a gap.
 */
const MEMBERS = [
  {
    id: 1,
    selector: '.scale-btn',
    media: null,
    state: 'rest',
    props: ['width', 'height', 'border-radius'],
    expect: { width: '28px', height: '28px', 'border-radius': '6px' },
  },
  {
    id: 2,
    selector: '.scale-btn:hover',
    media: null,
    state: 'hover',
    props: ['background-color', 'color'],
    controlClass: 'scale-btn',
  },
  {
    id: 3,
    selector: '.scale-btn:focus',
    media: null,
    state: 'focus',
    // `outline` is unobservable: a11y.css `*:focus { outline: none !important }`
    // beats this non-important declaration in every focus state. Only
    // `outline-offset` survives, and only while NOT `:focus-visible` (which
    // declares `outline-offset: 2px !important`).
    props: ['outline-offset'],
    expect: { 'outline-offset': '1px' },
    controlClass: 'scale-btn',
    note: 'outline is owned by the later `*:focus{outline:none!important}`; outline-offset is the only observable declaration',
  },
  {
    id: 4,
    selector: '.scale-btn.active',
    media: null,
    state: 'active-blurred',
    // Read with focus BLURRED: `*.active:focus { box-shadow: none !important }`
    // zeroes the shadow if the bearer is still focused.
    props: ['background-color', 'box-shadow'],
    controlClass: 'scale-btn',
  },
  {
    id: 5,
    selector: '.scale-btn.active:hover',
    media: null,
    state: 'active-hover',
    // --nav-accent-hover (#0055aa) vs member 4's --nav-accent (#0066cc).
    // navbar.css does NOT redefine either under [data-theme=dark], so this
    // separation holds in both themes.
    props: ['background-color'],
    controlClass: 'scale-btn active',
  },
  { id: 6, selector: '.scale-btn[data-scale="1"]', media: null, state: 'rest', dataScale: '1', props: ['font-size'], controlClass: 'scale-btn' },
  { id: 7, selector: '.scale-btn[data-scale="2"]', media: null, state: 'rest', dataScale: '2', props: ['font-size'], controlClass: 'scale-btn' },
  {
    id: 8,
    selector: '.scale-btn[data-scale="3"]',
    media: null,
    state: 'rest',
    dataScale: '3',
    props: ['font-size'],
    controlClass: 'scale-btn',
    computedBlind: true,
    note: 'font-size 0.75rem is byte-identical to member 1; only CDP source range separates them',
  },
  { id: 9, selector: '.scale-btn[data-scale="4"]', media: null, state: 'rest', dataScale: '4', props: ['font-size'], controlClass: 'scale-btn' },
  { id: 10, selector: '.scale-btn[data-scale="5"]', media: null, state: 'rest', dataScale: '5', props: ['font-size'], controlClass: 'scale-btn' },
  {
    id: 11,
    selector: '.scale-btn',
    media: `max-width: ${MEDIA_MAX}px`,
    state: 'rest',
    needsWidth: 991,
    props: ['flex-grow', 'flex-basis', 'max-width'],
    expect: { 'flex-grow': '1', 'flex-basis': '0%', 'max-width': '36px' },
  },
];

// The ten DISTINCT selector strings. Members 1 and 11 share `.scale-btn`, so a
// querySelectorAll census yields ten records, not eleven -- the census alone
// cannot separate them, which is why the per-member sentinels exist.
const CENSUS_SELECTORS = [...new Set(MEMBERS.map((m) => m.selector))];

// Known-live controls. d1 proved the oracle on these before believing anything
// it said about candidates; if these are not visible, no candidate result counts.
const LIVE_CONTROLS = ['.scale-control-compact', '.scale-btn-compact', '.scale-indicator', '[data-visual-scale-control]'];

// A class no document has ever carried. It must census 0 naturally AND become
// visible once injected -- that second half is what proves the synthetic
// mechanism works, rather than that the probe is simply blind.
const DEAD_CONTROL = 'ht-known-dead-control-a7f3';

const REST_PROPS = [
  'color',
  'background-color',
  'border-top-color',
  'border-top-width',
  'border-radius',
  'box-shadow',
  'display',
  'visibility',
  'opacity',
  'outline-color',
  'outline-offset',
  'font-size',
  'font-weight',
  'width',
  'height',
  'max-width',
  'flex-grow',
  'flex-basis',
  'padding-top',
  'margin-top',
];

const args = process.argv.slice(2);
const getArg = (flag, fallback) => {
  const index = args.indexOf(flag);
  return index === -1 ? fallback : args[index + 1];
};

const DOM_PATH_FN = `
  (el) => {
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && node !== document.documentElement) {
      const parent = node.parentElement;
      if (!parent) break;
      const index = Array.prototype.indexOf.call(parent.children, node);
      parts.unshift(node.tagName.toLowerCase() + '[' + index + ']');
      node = parent;
    }
    return 'html/' + parts.join('/');
  }
`;

/**
 * M6a. Suppress transitions and settle running animations before applying,
 * reading AND removing a sentinel. The CSS-only suppressor alone is beatable
 * (d2 measured this), so the Web Animations API is settled as well.
 */
const SUPPRESS_FN = `
  () => {
    let tag = document.getElementById('ht-scale-btn-suppressor');
    if (!tag) {
      tag = document.createElement('style');
      tag.id = 'ht-scale-btn-suppressor';
      tag.textContent = '*,*::before,*::after{transition:none !important;animation:none !important;}';
      document.head.appendChild(tag);
    }
    for (const animation of document.getAnimations()) {
      try { animation.finish(); } catch { animation.cancel(); }
    }
  }
`;

async function waitForServer() {
  const portOpen = () =>
    new Promise((done) => {
      const socket = connect({ host: '127.0.0.1', port: PORT });
      const settle = (value) => {
        socket.destroy();
        done(value);
      };
      socket.once('connect', () => settle(true));
      socket.once('error', () => settle(false));
      socket.setTimeout(1000, () => settle(false));
    });
  for (let attempt = 0; attempt < 180; attempt += 1) {
    if (await portOpen()) return true;
    await new Promise((done) => setTimeout(done, 500));
  }
  return false;
}

async function startServer() {
  const dbPath = resolve('artifacts/scale_btn/probe.db');
  mkdirSync(resolve('artifacts/scale_btn'), { recursive: true });
  for (const suffix of ['', '-wal', '-shm']) rmSync(`${dbPath}${suffix}`, { force: true });

  // A worktree created by `scripts/new-worktree.ps1` has no `.venv` of its own
  // (PARALLEL_WORKFLOW.md "Python environment"), so allow an explicit
  // interpreter. The default stays the repo-local venv.
  const python =
    process.env.HT_PROBE_PYTHON ??
    (process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python');
  const server = spawn(python, ['app.py'], {
    env: {
      ...process.env,
      DB_FILE: dbPath,
      HT_PORT: String(PORT),
      FLASK_DEBUG: '0',
      FLASK_USE_RELOADER: '0',
    },
    stdio: 'ignore',
  });
  if (!(await waitForServer())) {
    server.kill();
    throw new Error(`server did not come up at ${BASE_URL}`);
  }
  return server;
}

async function openPage(browser, theme) {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    colorScheme: theme,
    locale: 'en-US',
    timezoneId: 'UTC',
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();
  await page.addInitScript((value) => {
    localStorage.clear();
    localStorage.setItem('darkMode', value === 'dark' ? 'true' : 'false');
    document.documentElement?.setAttribute('data-theme', value);
  }, theme);
  return { context, page };
}

/** Set data-scale exactly as accessibility.js:82 and :89 do. */
async function applyScale(page, level) {
  await page.evaluate(
    ({ lvl, zoom }) => {
      document.documentElement.setAttribute('data-scale', String(lvl));
      document.documentElement.style.zoom = zoom;
    },
    { lvl: level, zoom: ZOOM_BY_SCALE[level] },
  );
}

/**
 * Phase 2: natural full-selector census, taken BEFORE any synthetic exists.
 * A rest-state differential cannot falsify an unreachable rule, so this is the
 * evidence that carries the "nothing matches" half of the claim.
 */
async function naturalCensus(page) {
  return page.evaluate(
    ({ selectors, live, dead }) => {
      const count = (sel) => document.querySelectorAll(sel).length;
      const out = { candidates: {}, live: {}, dead: 0 };
      for (const sel of selectors) out.candidates[sel] = count(sel);
      for (const sel of live) out.live[sel] = count(sel);
      out.dead = count(`.${dead}`);
      return out;
    },
    { selectors: CENSUS_SELECTORS, live: LIVE_CONTROLS, dead: DEAD_CONTROL },
  );
}

async function captureRestState(page) {
  return page.evaluate(
    ({ propList, domPathSource }) => {
      const domPath = eval(domPathSource);
      const records = [];
      for (const element of document.querySelectorAll('body *')) {
        const tag = element.tagName.toLowerCase();
        if (tag === 'script' || tag === 'style') continue;
        const computed = getComputedStyle(element);
        const values = {};
        for (const prop of propList) values[prop] = computed.getPropertyValue(prop);
        records.push({ path: domPath(element), tag, values });
      }
      return records;
    },
    { propList: REST_PROPS, domPathSource: DOM_PATH_FN },
  );
}

/**
 * Phase 3. Inject a bearer that satisfies the member's full selector and a
 * control that fails it by exactly ONE compound, then read properties derived
 * from the member's own declarations.
 *
 * Returns the sentinel reading plus an explicit `reverted` check: a probe that
 * changes nothing proves nothing, and one that fails to clean up has silently
 * edited the page it is measuring.
 */
async function certifyMember(page, member) {
  if (member.needsWidth) {
    await page.setViewportSize({ width: member.needsWidth, height: 900 });
  }
  await page.evaluate(`(${SUPPRESS_FN})()`);

  await page.evaluate(
    ({ dataScale, dead, controlClass }) => {
      const make = (id, cls) => {
        const el = document.createElement('button');
        el.id = id;
        el.type = 'button';
        if (cls) el.className = cls;
        // Identical text on BOTH so each keeps a bounding box once the
        // family is deleted; a 0x0 button is unhoverable and unclickable,
        // which would read as a harness failure in the after run.
        el.textContent = 'A';
        document.body.appendChild(el);
        return el;
      };
      document.getElementById('ht-bearer')?.remove();
      document.getElementById('ht-control')?.remove();
      const bearer = make('ht-bearer', 'scale-btn');
      // The control must fail the member's selector by EXACTLY ONE compound.
      // For members 2-10 that means the control is itself a `.scale-btn` minus
      // the one distinguishing compound -- otherwise the reading is taken
      // against the INHERITED value rather than against the base rule, which
      // silently hid member 9 (0.8rem == the inherited 12.8px) in the first run.
      const control = make('ht-control', controlClass || dead);
      if (dataScale) bearer.setAttribute('data-scale', dataScale);
    },
    { dataScale: member.dataScale ?? null, dead: DEAD_CONTROL, controlClass: member.controlClass ?? null },
  );

  // Drive the real interaction state. CDP pseudo-forcing is done separately in
  // the owner pass; this half must be a genuine browser state.
  if (member.state === 'hover' || member.state === 'active-hover') {
    if (member.state === 'active-hover') {
      await page.evaluate(() => document.getElementById('ht-bearer')?.classList.add('active'));
    }
    await page.hover('#ht-bearer', { force: true });
  } else if (member.state === 'focus') {
    // A mouse click yields `:focus` WITHOUT `:focus-visible`, which is the only
    // state in which member 3's `outline-offset` can be observed at all.
    await page.click('#ht-bearer', { force: true });
  } else if (member.state === 'active-blurred') {
    await page.evaluate(() => {
      const el = document.getElementById('ht-bearer');
      el?.classList.add('active');
      el?.blur();
    });
  }

  await page.evaluate(`(${SUPPRESS_FN})()`);

  const reading = await page.evaluate(
    ({ props, state }) => {
      const bearer = document.getElementById('ht-bearer');
      const control = document.getElementById('ht-control');
      if (!bearer || !control) return null;
      const b = getComputedStyle(bearer);
      const c = getComputedStyle(control);
      const values = {};
      const controlValues = {};
      for (const prop of props) {
        values[prop] = b.getPropertyValue(prop);
        controlValues[prop] = c.getPropertyValue(prop);
      }
      return {
        values,
        controlValues,
        matchesFocus: bearer.matches(':focus'),
        matchesFocusVisible: bearer.matches(':focus-visible'),
        matchesHover: bearer.matches(':hover'),
        hasActive: bearer.classList.contains('active'),
        state,
      };
    },
    { props: member.props, state: member.state },
  );

  const cdp = await matchedScaleBtnRules(page, '#ht-bearer', member);

  // Remove the synthetics while transitions are still suppressed (M6a is
  // symmetric), then confirm the page is back to its natural census.
  const reverted = await page.evaluate(() => {
    document.getElementById('ht-bearer')?.remove();
    document.getElementById('ht-control')?.remove();
    return document.querySelectorAll('.scale-btn').length;
  });

  if (member.needsWidth) {
    await page.setViewportSize({ width: 1440, height: 900 });
  }

  const differs =
    reading &&
    member.props.some((p) => reading.values[p] !== reading.controlValues[p]);

  // Where the member declares an absolute value, check the bearer actually
  // landed on it. "Differs from its control" alone would accept a bearer that
  // picked up the right rule for the wrong reason.
  const expected = member.expect ?? null;
  const expectationsMet = expected
    ? Object.entries(expected).every(([prop, want]) => reading?.values[prop] === want)
    : null;

  return {
    member: member.id,
    selector: member.selector,
    media: member.media,
    state: member.state,
    computedBlind: Boolean(member.computedBlind),
    note: member.note ?? null,
    reading,
    // "Took effect" = the bearer's value differs from a control that fails the
    // selector by exactly one compound. For `computedBlind` members this is
    // expected to be false and is NOT a failure -- CDP carries them.
    tookEffect: Boolean(differs),
    expected,
    expectationsMet,
    cdpRules: cdp,
    revertedToZeroBearers: reverted === 0,
  };
}

/**
 * Phase 4: declaration-owner evidence. This is the only oracle that can state
 * the flip BY SOURCE IDENTITY rather than as "the rule went blind" -- a phrase
 * indistinguishable from "the oracle stopped working".
 *
 * Pseudo-states are forced through CDP so every member's rule is in the matched
 * set regardless of real pointer position.
 */
async function matchedScaleBtnRules(page, selector, member) {
  const client = await page.context().newCDPSession(page);
  try {
    await client.send('DOM.enable');
    await client.send('CSS.enable');
    const { root } = await client.send('DOM.getDocument', { depth: -1, pierce: false });
    const { nodeId } = await client.send('DOM.querySelector', { nodeId: root.nodeId, selector });
    if (!nodeId) return { error: 'bearer node not found', rules: [] };

    await client.send('CSS.forcePseudoState', {
      nodeId,
      forcedPseudoClasses: ['hover', 'focus', 'active'],
    });

    const matched = await client.send('CSS.getMatchedStylesForNode', { nodeId });
    const rules = (matched.matchedCSSRules ?? [])
      .filter((entry) => entry.rule?.origin === 'regular')
      .map((entry) => ({
        selector: entry.rule.selectorList?.text ?? '',
        media: (entry.rule.media ?? []).map((m) => m.text),
        // `style.range` is the DECLARATION-BLOCK range, not the whole rule --
        // d1 defect #7. Reported as 1-based lines to match d1's proven unit.
        declarationBlock: entry.rule.style?.range
          ? {
              startLine: entry.rule.style.range.startLine + 1,
              endLine: entry.rule.style.range.endLine + 1,
            }
          : null,
        selectorRange: entry.rule.selectorList?.range
          ? {
              startLine: entry.rule.selectorList.range.startLine + 1,
              endLine: entry.rule.selectorList.range.endLine + 1,
            }
          : null,
        declarations: (entry.rule.style?.cssProperties ?? [])
          .filter((p) => !p.disabled && p.name && p.range)
          .map((p) => ({ name: p.name, value: p.value, important: Boolean(p.important) })),
      }))
      // Exact class token. `.scale-btn-compact` must never be counted here --
      // it is the live generation and the oracle-validity control.
      .filter((r) => /\.scale-btn(?![\w-])/.test(r.selector));

    await client.send('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: [] });
    return { error: null, memberId: member?.id ?? null, rules };
  } catch (error) {
    return { error: String(error), rules: [] };
  } finally {
    await client.detach().catch(() => {});
  }
}

function diffRecords(before, after) {
  const index = new Map(before.map((r) => [r.path, r]));
  let compared = 0;
  const differing = [];
  for (const rec of after) {
    const prev = index.get(rec.path);
    if (!prev) continue;
    for (const [prop, value] of Object.entries(rec.values)) {
      compared += 1;
      if (prev.values[prop] !== value) {
        differing.push({ path: rec.path, prop, before: prev.values[prop], after: value });
      }
    }
  }
  return { compared, differingCount: differing.length, differing: differing.slice(0, 200) };
}

async function run(outDir) {
  // `--out` is fed straight to a recursive rmSync, so refuse anything outside
  // the gitignored artifacts tree rather than trusting a typo.
  if (!resolve(outDir).startsWith(resolve('artifacts'))) {
    throw new Error(`--out must resolve under artifacts/ (got ${resolve(outDir)})`);
  }
  rmSync(outDir, { recursive: true, force: true });
  mkdirSync(outDir, { recursive: true });

  const server = await startServer();
  const browser = await chromium.launch({
    args: ['--disable-font-subpixel-positioning', '--disable-gpu', '--force-color-profile=srgb'],
  });

  try {
    return await sweep(browser, outDir);
  } finally {
    // Without this, any throw mid-sweep orphans a headless Chromium AND a
    // `python app.py` still holding the probe port, so the NEXT run fails in
    // waitForServer() for an unrelated reason.
    await browser.close().catch(() => {});
    server.kill();
  }
}

async function sweep(browser, outDir) {
  const report = {
    baseUrl: BASE_URL,
    generatedBy: 'scripts/css_audit/scale_btn_census.mjs',
    matrix: { routes: ROUTES.length, themes: THEMES.length, widths: WIDTHS.length, scales: SCALES.length },
    census: { contexts: 0, candidates: {}, live: {}, deadControlNonZero: 0 },
    printContexts: 0,
    reducedMotionContexts: 0,
    certification: [],
    deadControlInjectionVisible: null,
    sameCssControl: null,
  };
  for (const sel of CENSUS_SELECTORS) report.census.candidates[sel] = { zero: 0, nonZero: 0, max: 0 };
  for (const sel of LIVE_CONTROLS) report.census.live[sel] = { zero: 0, nonZero: 0, max: 0 };

  const restRecords = [];
  let sameCssA = null;
  let sameCssB = null;

  for (const theme of THEMES) {
    for (const route of ROUTES) {
      const { context, page } = await openPage(browser, theme);
      await page.goto(`${BASE_URL}${route.path}`, { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle').catch(() => {});
      await page.evaluate(() => document.fonts.ready).catch(() => {});
      await page.waitForTimeout(400);

      // --- Phase 2: natural census, before ANY synthetic exists -------------
      for (const width of WIDTHS) {
        await page.setViewportSize({ width, height: 900 });
        for (const scale of SCALES) {
          await applyScale(page, scale);
          const c = await naturalCensus(page);
          report.census.contexts += 1;
          for (const [sel, n] of Object.entries(c.candidates)) {
            if (n === 0) report.census.candidates[sel].zero += 1;
            else {
              report.census.candidates[sel].nonZero += 1;
              report.census.candidates[sel].max = Math.max(report.census.candidates[sel].max, n);
            }
          }
          for (const [sel, n] of Object.entries(c.live)) {
            if (n === 0) report.census.live[sel].zero += 1;
            else {
              report.census.live[sel].nonZero += 1;
              report.census.live[sel].max = Math.max(report.census.live[sel].max, n);
            }
          }
          if (c.dead !== 0) report.census.deadControlNonZero += 1;
        }
      }

      // --- print + reduced motion, under their own conditions --------------
      await page.setViewportSize({ width: 1440, height: 900 });
      await applyScale(page, 6);
      await page.emulateMedia({ media: 'print' });
      const printCensus = await naturalCensus(page);
      report.printContexts += 1;
      for (const [sel, n] of Object.entries(printCensus.candidates)) {
        if (n === 0) report.census.candidates[sel].zero += 1;
        else report.census.candidates[sel].nonZero += 1;
      }
      await page.emulateMedia({ media: 'screen', reducedMotion: 'reduce' });
      const rmCensus = await naturalCensus(page);
      report.reducedMotionContexts += 1;
      for (const [sel, n] of Object.entries(rmCensus.candidates)) {
        if (n === 0) report.census.candidates[sel].zero += 1;
        else report.census.candidates[sel].nonZero += 1;
      }
      await page.emulateMedia({ media: 'screen', reducedMotion: 'no-preference' });

      // --- Phase 5: rest state ---------------------------------------------
      await page.evaluate(`(${SUPPRESS_FN})()`);
      const rest = await captureRestState(page);
      restRecords.push({ route: route.name, theme, records: rest });

      // --- same-CSS control: identical capture twice, must be zero ---------
      // Same-CSS control (M5): the IDENTICAL capture twice, in the SAME context
      // and theme. Seeding `sameCssA` from the light pass and `sameCssB` from
      // the dark pass compares two different stylesheets and reports thousands
      // of spurious differences -- measured at 14,601/97,600 before this fix.
      if (route.name === 'workout-plan' && theme === 'light') {
        sameCssA = rest;
        sameCssB = await captureRestState(page);
      }

      // --- Phase 3 + 4: certification, on one representative context -------
      if (route.name === 'welcome') {
        // The known-dead control must be invisible naturally AND visible once
        // injected; without the second half a blind probe looks like a clean one.
        const deadVisible = await page.evaluate((cls) => {
          const el = document.createElement('div');
          el.className = cls;
          document.body.appendChild(el);
          const seen = document.querySelectorAll(`.${cls}`).length;
          el.remove();
          return seen;
        }, DEAD_CONTROL);
        report.deadControlInjectionVisible = deadVisible;

        for (const member of MEMBERS) {
          const result = await certifyMember(page, member);
          report.certification.push({ ...result, theme, route: route.name });
        }
      }

      await context.close();
    }
  }

  if (sameCssA && sameCssB) report.sameCssControl = diffRecords(sameCssA, sameCssB);

  writeFileSync(resolve(outDir, 'report.json'), JSON.stringify(report, null, 2), 'utf8');
  writeFileSync(resolve(outDir, 'reststate.json'), JSON.stringify(restRecords), 'utf8');

  summarize(report);

  const deadLive = Object.entries(report.census.live).filter(([, v]) => v.nonZero === 0);
  const controlsOk =
    deadLive.length === 0 &&
    report.census.deadControlNonZero === 0 &&
    (report.deadControlInjectionVisible ?? 0) > 0 &&
    (report.sameCssControl?.differingCount ?? 1) === 0;
  console.log(`
  oracle validity gate: ${controlsOk ? 'PASS' : '** FAIL — every candidate result from this run is void **'}`);
  if (!controlsOk) process.exitCode = 1;

  return report;
}

function summarize(report) {
  const total = report.census.contexts + report.printContexts + report.reducedMotionContexts;
  console.log('\n=== oracle validity ===');
  for (const [sel, s] of Object.entries(report.census.live)) {
    console.log(`  LIVE control ${sel.padEnd(28)} nonZero ${s.nonZero}/${report.census.contexts} (max ${s.max})`);
  }
  console.log(`  DEAD control natural non-zero contexts : ${report.census.deadControlNonZero} (must be 0)`);
  console.log(`  DEAD control visible when injected     : ${report.deadControlInjectionVisible} (must be > 0)`);
  if (report.sameCssControl) {
    console.log(
      `  same-CSS control                       : ${report.sameCssControl.differingCount} differing / ${report.sameCssControl.compared} compared (must be 0)`,
    );
  }

  console.log('\n=== natural full-selector census (before any injection) ===');
  for (const [sel, s] of Object.entries(report.census.candidates)) {
    console.log(`  ${sel.padEnd(30)} zero ${s.zero}/${total}  nonZero ${s.nonZero}  max ${s.max}`);
  }

  console.log('\n=== per-member certification ===');
  for (const c of report.certification) {
    const rules = c.cdpRules?.rules ?? [];
    const own = rules.filter(
      (r) => r.selector.trim() === c.selector.trim() && (c.media ? r.media.join('|').includes('991.98') : true),
    );
    console.log(
      `  member ${String(c.member).padStart(2)} ${c.selector.padEnd(28)} ` +
        `tookEffect=${String(c.tookEffect).padEnd(5)} cdpRules=${rules.length} ownRule=${own.length} ` +
        `reverted=${c.revertedToZeroBearers}${c.computedBlind ? '  [computed-blind: CDP-only by design]' : ''}`,
    );
  }
}

function diffRuns(beforeDir, afterDir) {
  const before = JSON.parse(readFileSync(resolve(beforeDir, 'report.json'), 'utf8'));
  const after = JSON.parse(readFileSync(resolve(afterDir, 'report.json'), 'utf8'));
  const beforeRest = JSON.parse(readFileSync(resolve(beforeDir, 'reststate.json'), 'utf8'));
  const afterRest = JSON.parse(readFileSync(resolve(afterDir, 'reststate.json'), 'utf8'));

  let compared = 0;
  let differingCount = 0;
  const samples = [];
  const afterIndex = new Map(afterRest.map((r) => [`${r.route}|${r.theme}`, r.records]));
  for (const entry of beforeRest) {
    const other = afterIndex.get(`${entry.route}|${entry.theme}`);
    if (!other) continue;
    const d = diffRecords(entry.records, other);
    compared += d.compared;
    differingCount += d.differingCount;
    for (const rec of d.differing.slice(0, 5)) samples.push({ route: entry.route, theme: entry.theme, ...rec });
  }

  console.log('\n=== rest-state differential (before vs after) ===');
  console.log(`  compared  : ${compared}`);
  console.log(`  differing : ${differingCount}`);
  for (const s of samples.slice(0, 20)) {
    console.log(`    ${s.route}/${s.theme} ${s.path} ${s.prop}: ${s.before} -> ${s.after}`);
  }

  console.log('\n=== candidate-inventory flip, by source identity ===');
  const key = (c) => `${c.member}|${c.theme}`;
  const beforeById = new Map(before.certification.map((c) => [key(c), c]));
  const afterById = new Map(after.certification.map((c) => [key(c), c]));
  const themes = [...new Set(before.certification.map((c) => c.theme))].sort();
  let flipped = 0;
  let expectedFlips = 0;
  for (const member of MEMBERS) {
   for (const theme of themes) {
    expectedFlips += 1;
    const b = beforeById.get(`${member.id}|${theme}`);
    const a = afterById.get(`${member.id}|${theme}`);
    const ownBefore = (b?.cdpRules?.rules ?? []).filter(
      (r) => r.selector.trim() === member.selector.trim() && (member.media ? r.media.join('|').includes('991.98') : r.media.length === 0),
    );
    const ownAfter = (a?.cdpRules?.rules ?? []).filter(
      (r) => r.selector.trim() === member.selector.trim() && (member.media ? r.media.join('|').includes('991.98') : r.media.length === 0),
    );
    const range = ownBefore[0]?.declarationBlock;
    // A CDP failure also returns rules:[]. Scoring that as a flip is exactly
    // the "the oracle stopped working" confusion this harness exists to
    // prevent, so an errored side can never count as proof.
    const oracleOk = b?.cdpRules?.error == null && a?.cdpRules?.error == null;
    const ok = oracleOk && ownBefore.length > 0 && ownAfter.length === 0;
    if (ok) flipped += 1;
    const why = !oracleOk ? '** ORACLE ERROR — NOT PROVEN **' : ok ? 'FLIPPED' : '** NOT PROVEN **';
    console.log(
      `  member ${String(member.id).padStart(2)} [${theme.padEnd(5)}] ${member.selector.padEnd(28)} ` +
        `before=${ownBefore.length}${range ? ` @lines ${range.startLine}-${range.endLine}` : ''} after=${ownAfter.length} ` +
        `${why}`,
    );
   }
  }
  console.log(`\n  flipped ${flipped}/${expectedFlips} (members × themes)`);

  // The after-run's own controls must still hold, or a flip means nothing.
  const liveAfter = Object.entries(after.census?.live ?? {}).filter(([, v]) => v.nonZero === 0);
  const controlsOk =
    liveAfter.length === 0 &&
    after.census?.deadControlNonZero === 0 &&
    (after.deadControlInjectionVisible ?? 0) > 0 &&
    (after.sameCssControl?.differingCount ?? 1) === 0;
  console.log(`  after-run oracle validity : ${controlsOk ? 'PASS' : '** FAIL **'}`);
  if (liveAfter.length) console.log(`    dead live-controls: ${liveAfter.map(([k]) => k).join(', ')}`);

  if (!controlsOk || flipped !== expectedFlips || differingCount !== 0) process.exitCode = 1;
  return { compared, differingCount, flipped, expectedFlips, controlsOk };
}

const diffPair = args.indexOf('--diff');
if (diffPair !== -1) {
  diffRuns(args[diffPair + 1], args[diffPair + 2]);
} else {
  await run(resolve(getArg('--out', 'artifacts/scale_btn/run')));
}
