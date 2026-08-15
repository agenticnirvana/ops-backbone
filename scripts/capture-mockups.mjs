#!/usr/bin/env node
/**
 * Capture Platform UI v3.4 screenshots for walkthrough mockups.
 * Requires: gateway at http://localhost:8080, playwright (npm i -D playwright in scripts/)
 */
import { chromium } from 'playwright';
import { copyFileSync, mkdirSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');
const OUT = join(ROOT, 'images', 'mockups');
const BASE = process.env.MOCKUP_BASE_URL || 'http://localhost:8080';

const SCENES = [
  'step-01b-runbook-ingestion',
  'step-01-ingestion-observability',
  'step-02-agent-orchestration',
  'step-03-langfuse-trace',
  'step-04-mlflow-evals',
  'step-05-hitl-opa-guardrails',
  'step-06-ticket-action',
];

mkdirSync(OUT, { recursive: true });

async function captureScene(page, scene) {
  await page.goto(`${BASE}/?capture=${scene}`, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(
    (key) => document.title === `CAPTURE_READY:${key}`,
    scene,
    { timeout: 30000 },
  );
  await page.waitForTimeout(800);
  const out = join(OUT, `${scene}.png`);
  await page.screenshot({ path: out, fullPage: false });
  console.log(`✓ ${scene}.png`);
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 2,
});
const page = await context.newPage();

try {
  for (const scene of SCENES) {
    await captureScene(page, scene);
  }

  copyFileSync(
    join(ROOT, 'images', 'architecture-diagram.png'),
    join(OUT, 'step-00-architecture-overview.png'),
  );
  console.log('✓ step-00-architecture-overview.png (from architecture-diagram.png)');
} finally {
  await browser.close();
}

console.log(`\nMockups saved to ${OUT}`);
