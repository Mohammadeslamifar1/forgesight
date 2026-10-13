import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mkdir } from 'node:fs/promises';

test('real model inspection, heatmap, review, export, and history', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Anomalies, in focus.' })).toBeVisible();
  await page.getByRole('button', { name: 'Run inspection', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Review recommended' })).toBeVisible();
  await expect(page.getByAltText('Anomaly overlay')).toBeVisible();
  await mkdir('../docs/images', { recursive: true });
  await page.screenshot({ path: '../docs/images/inspection.png', fullPage: true });
  await page.getByRole('button', { name: 'Heatmap', exact: true }).click();
  await expect(page.getByAltText('Anomaly distance heatmap')).toBeVisible();
  await page.getByLabel('Defect observed', { exact: true }).check();
  await page.getByLabel('Review rationale').fill('Visible missing glass at the bottle rim.');
  await page.getByRole('button', { name: 'Record review', exact: true }).click();
  await expect(
    page.getByText('Visible missing glass at the bottle rim.', { exact: true }),
  ).toBeVisible();
  const downloaded = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Export inspection record' }).click();
  expect((await downloaded).suggestedFilename()).toMatch(/forgesight-.*\.json/);
  await page.getByRole('button', { name: 'Inspection history', exact: true }).click();
  await page.locator('.history-row').first().click();
  await expect(
    page.getByText('Visible missing glass at the bottle rim.', { exact: true }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test('normal sample, upload validation, and sample gallery', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /Normal reference/ }).click();
  await page.getByRole('button', { name: 'Run inspection', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Within normal range' })).toBeVisible();
  await page.getByLabel('Upload inspection image').setInputFiles({
    name: 'bad.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('not an image'),
  });
  await expect(page.getByRole('alert')).toContainText('PNG or JPEG');
  await page.getByRole('button', { name: /All 83 samples/ }).click();
  await page.getByLabel('Select any held-out test image').selectOption('contamination-001');
  await page.getByRole('button', { name: 'Run inspection', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Review recommended' })).toBeVisible();
});

test('threshold exploration never mutates the fitted model', async ({ page, request }) => {
  const before = await (await request.get('/api/model')).json();
  await page.goto('/#benchmark');
  await expect(page.getByRole('heading', { name: 'Measure what matters.' })).toBeVisible();
  await page.getByLabel('Sandbox anomaly threshold').fill('4');
  await expect(page.locator('.threshold-reading > strong')).toHaveText('4.000');
  await page.getByRole('button', { name: /Calibrated:/ }).click();
  await expect(page.locator('.threshold-reading > strong')).toHaveText(
    before.metadata.calibration.threshold.toFixed(3),
  );
  const after = await (await request.get('/api/model')).json();
  expect(after.metadata).toEqual(before.metadata);
  await page.screenshot({ path: '../docs/images/benchmark.png', fullPage: true });
});

test('uploaded images can be reviewed from history without rerunning an unrelated sample', async ({
  page,
  request,
}) => {
  const sample = await request.get('/api/samples/good-000/image');
  await page.goto('/');
  await page.getByLabel('Upload inspection image').setInputFiles({
    name: 'uploaded-bottle.png',
    mimeType: 'image/png',
    buffer: await sample.body(),
  });
  await page.getByRole('button', { name: 'Run inspection', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Within normal range' })).toBeVisible();
  await page.getByRole('button', { name: 'Inspection history', exact: true }).click();
  await page.locator('.history-row').filter({ hasText: 'uploaded-bottle.png' }).first().click();
  await expect(page.getByRole('button', { name: 'Choose an input to inspect' })).toBeDisabled();
  await page.getByRole('button', { name: /Normal reference/ }).click();
  await expect(page.getByRole('button', { name: 'Run inspection', exact: true })).toBeEnabled();
});

test('model card and browser history routes work', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Model card', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Nothing behind the curtain.' })).toBeVisible();
  await expect(page.getByText('CC-BY-NC-SA-4.0', { exact: true })).toBeVisible();
  await page.goBack();
  await expect(page.getByRole('heading', { name: 'Anomalies, in focus.' })).toBeVisible();
});

test('mobile navigation and layout fit the viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Anomalies, in focus.' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.screenshot({ path: '../docs/images/mobile.png', fullPage: true });
  await page.getByRole('button', { name: 'Open navigation' }).click();
  await page.getByRole('button', { name: 'Model performance', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Measure what matters.' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
});

test('inspection studio has no automated WCAG AA violations', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Anomalies, in focus.' })).toBeVisible();
  const result = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();
  expect(result.violations).toEqual([]);
});
