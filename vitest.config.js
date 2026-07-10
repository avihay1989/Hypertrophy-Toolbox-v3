import { defineConfig } from 'vitest/config';

// Plain-JavaScript Vitest scaffold (Refactor Plan v3 WP3.1). No TypeScript.
//
// `environment: 'node'` is the default because the seeded suite covers only
// genuinely pure helpers (no DOM). DOM/Bootstrap modules (e.g. toast.js) are
// deferred; when they are tested they must opt into jsdom per-file with a
//   // @vitest-environment jsdom
// docblock and stand up explicit DOM + Bootstrap fakes — never treated as
// trivial pure helpers. `jsdom` is installed as a devDependency for that use.
//
// `include` is scoped to co-located `*.test.js` files under static/js so this
// runner never collides with the Playwright E2E suite (e2e/*.spec.ts) or the
// pytest suite (tests/test_*.py).
export default defineConfig({
    test: {
        environment: 'node',
        include: ['static/js/**/*.test.js'],
    },
});
