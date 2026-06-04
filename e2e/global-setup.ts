import { execFileSync } from 'child_process';
import fs from 'fs';
import path from 'path';

/**
 * Absolute path of the throwaway SQLite DB the E2E web server runs against.
 * Lives under the gitignored `artifacts/` tree, so it never touches the
 * developer's tracked `data/database.db`. `playwright.config.ts` points the
 * web server's `DB_FILE` here.
 */
export const E2E_DB_PATH = path.join(process.cwd(), 'artifacts', 'e2e', 'database.e2e.db');

function resolvePython(): string {
  const venv = process.platform === 'win32'
    ? path.join(process.cwd(), '.venv', 'Scripts', 'python.exe')
    : path.join(process.cwd(), '.venv', 'bin', 'python');
  return fs.existsSync(venv) ? venv : 'python';
}

/**
 * Seed a fresh, deterministic E2E database before the suite runs: full exercise
 * catalog, empty user-state. Reproduced from the committed visual seed via
 * `e2e/scripts/prepare_e2e_db.py`, so the suite never depends on local data.
 *
 * Skipped when reusing an already-running server (`PW_REUSE_SERVER=1`) — that
 * server owns whatever DB it was started with, and reseeding under it would
 * corrupt WAL state mid-run.
 */
export default async function globalSetup(): Promise<void> {
  if (process.env.PW_REUSE_SERVER === '1' && !process.env.CI) {
    return;
  }
  const python = resolvePython();
  const seed = path.join(process.cwd(), 'e2e', 'fixtures', 'database.visual.seed.db');
  execFileSync(
    python,
    [
      path.join('e2e', 'scripts', 'prepare_e2e_db.py'),
      '--source', seed,
      '--output', E2E_DB_PATH,
    ],
    { stdio: 'inherit' },
  );
}
