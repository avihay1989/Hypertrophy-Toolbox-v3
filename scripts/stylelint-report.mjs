import { createHash } from 'node:crypto';
import { appendFileSync, readFileSync, writeFileSync } from 'node:fs';
import { relative } from 'node:path';

const [, , inputPath, outputPath, baselinePath] = process.argv;

if (!inputPath || !outputPath) {
  console.error(
    'usage: node scripts/stylelint-report.mjs <raw.json> <summary.json> [baseline.json]',
  );
  process.exit(2);
}

const rawText = readFileSync(inputPath, 'utf8');
const results = JSON.parse(rawText);
const packageJson = JSON.parse(readFileSync('package.json', 'utf8'));
const warnings = results.flatMap((result) => result.warnings ?? []);

const increment = (record, key) => {
  record[key] = (record[key] ?? 0) + 1;
};

const byRule = {};
for (const warning of warnings) {
  increment(byRule, warning.rule ?? '<unknown>');
}

const byFile = {};
for (const result of results) {
  const file = relative(process.cwd(), result.source).replaceAll('\\', '/');
  byFile[file] = (result.warnings ?? []).length;
}

const sortRecord = (record) => Object.fromEntries(
  Object.entries(record).sort(([left], [right]) => left.localeCompare(right)),
);

const summary = {
  schemaVersion: 1,
  tools: {
    stylelint: packageJson.devDependencies.stylelint,
    postcssScss: packageJson.devDependencies['postcss-scss'],
  },
  sources: [
    'static/css/**/*.css',
    'scss/**/*.scss',
  ],
  exclusions: [
    'static/css/bootstrap.custom.min.css',
    'static/css/bootstrap.custom.min.css.map',
  ],
  fileCount: results.length,
  filesWithWarnings: results.filter((result) => (result.warnings ?? []).length > 0).length,
  warningCount: warnings.length,
  erroredFileCount: results.filter((result) => result.errored).length,
  parseErrorCount: results.reduce(
    (total, result) => total + (result.parseErrors ?? []).length,
    0,
  ),
  invalidOptionWarningCount: results.reduce(
    (total, result) => total + (result.invalidOptionWarnings ?? []).length,
    0,
  ),
  rawReportSha256: createHash('sha256').update(rawText).digest('hex'),
  byRule: sortRecord(byRule),
  byFile: sortRecord(byFile),
};

writeFileSync(outputPath, `${JSON.stringify(summary, null, 2)}\n`);

const lines = [
  '### CSS stylelint measurement (non-blocking)',
  `- **warnings**: ${summary.warningCount} across ${summary.filesWithWarnings}/${summary.fileCount} files`,
  `- **parse/config errors**: ${summary.parseErrorCount}/${summary.invalidOptionWarningCount}`,
];

if (baselinePath) {
  const baseline = JSON.parse(readFileSync(baselinePath, 'utf8'));
  const delta = summary.warningCount - baseline.warningCount;
  const sign = delta > 0 ? '+' : '';
  lines.push(`- **baseline delta**: ${sign}${delta} vs ${baseline.warningCount}`);
}

const markdown = `${lines.join('\n')}\n`;
process.stdout.write(markdown);

if (process.env.GITHUB_STEP_SUMMARY) {
  appendFileSync(process.env.GITHUB_STEP_SUMMARY, markdown);
}
