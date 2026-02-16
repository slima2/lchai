/**
 * Captures a full-page screenshot of the LCHAI v1.2 case overview (Images tab)
 * for TCGA-69-7979. Requires the stack running at http://localhost:3000.
 *
 * Usage: from oncology-xai root:
 *   npx playwright install chromium
 *   node scripts/capture-case-overview-screenshot.mjs
 *
 * Output: docs/figures/case_overview_output.png
 */

import { chromium } from 'playwright';
import { mkdirSync, existsSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const outDir = join(__dirname, '..', 'docs', 'figures');
const outPath = join(outDir, 'case_overview_output.png');

if (!existsSync(outDir)) {
  mkdirSync(outDir, { recursive: true });
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // Match typical viewport for a desktop screenshot
  await page.setViewportSize({ width: 1400, height: 900 });

  try {
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle', timeout: 15000 });
  } catch (e) {
    console.error('Failed to load http://localhost:3000. Is the webapp running? (e.g. docker compose up -d)');
    await browser.close();
    process.exit(1);
  }

  // Wait for auto-load: default case TCGA-69-7979 and Images tab with results
  await page.waitForTimeout(3000);
  // Wait for content that indicates the case overview is visible (pattern table or mutation table)
  try {
    await page.waitForSelector('text=Pattern Composition', { timeout: 12000 });
  } catch {
    // Optional: page may still have loaded
  }
  await page.waitForTimeout(2000);

  await page.screenshot({
    path: outPath,
    fullPage: true,
  });

  await browser.close();
  console.log('Screenshot saved to:', outPath);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
