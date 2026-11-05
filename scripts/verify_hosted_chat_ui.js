// Explicit live acceptance. Running this callback consumes real provider quota.
async function verifyHostedChatUI(page) {
  const assert = (value, message) => { if (!value) throw new Error(message); };
  assert(new URL(page.url()).origin === 'https://databuddy-demo.pages.dev', 'Requires the approved hosted frontend');
  await page.addInitScript(() => {
    const original = window.addEventListener;
    window.addEventListener = function(type, ...args) {
      if (type !== 'beforeunload') original.call(this, type, ...args);
    };
  });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  const idle = () => page.waitForFunction(() => {
    const send = document.querySelector('[aria-label="Send message"]');
    return send && !send.disabled;
  }, undefined, { timeout: 150000 });
  await idle();
  await page.getByRole('heading', { name: 'Hi, I’m DataBuddy', exact: true }).waitFor();
  const lastAnswer = () => page.locator('.message-assistant .prose').last().textContent();
  let submissions = 0;
  const send = async text => {
    await idle();
    const before = await page.locator('.message-assistant').count();
    await page.getByRole('textbox', { name: 'Question about your data' }).fill(text);
    await page.getByRole('button', { name: 'Send message', exact: true }).click();
    submissions++;
    await page.waitForFunction(count => document.querySelectorAll('.message-assistant').length > count, before, { timeout: 150000 });
    await idle();
  };
  await send('Hi, my name is Asha. Please keep replies brief.');
  assert(/asha/i.test(await lastAnswer()), 'Actual greeting before upload');
  await send('Please call me Sky instead.');
  await send('What name should you call me?');
  assert(/\bSky\b/i.test(await lastAnswer()), 'Actual corrected-name recall');
  await page.reload();
  await idle();
  assert(/\bSky\b/i.test(await lastAnswer()), 'Hosted reload restores chat');
  const turns = await page.locator('.message-assistant').count();
  await page.getByRole('button', { name: 'Choose dataset' }).setInputFiles('output/playwright/hosted-upload.csv');
  await page.waitForFunction(() => !!document.querySelector('.composer-file'), undefined, { timeout: 120000 });
  await idle();
  assert(await page.locator('.message-assistant').count() === turns, 'Real CSV first upload preserves chat');
  await send('What name should you call me now?');
  assert(/\bSky\b/i.test(await lastAnswer()), 'Actual recall after CSV upload');
  await send('What is the total Sales across all rows?');
  await page.getByRole('button', { name: 'Result data', exact: true }).last().waitFor();
  assert(/1,?000/.test(await lastAnswer()), 'Actual computed total');
  await send('Create a bar chart of total Sales by Region.');
  await page.getByRole('button', { name: 'Open interactive chart', exact: false }).last().click();
  await page.getByRole('dialog').locator('.js-plotly-plot').waitFor({ timeout: 120000 });
  const pngWait = page.waitForEvent('download');
  await page.getByRole('button', { name: /PNG/i }).click();
  const png = await pngWait;
  await png.saveAs('output/playwright/hosted-chart.png');
  const htmlWait = page.waitForEvent('download');
  await page.getByRole('button', { name: /HTML/i }).click();
  const html = await htmlWait;
  await html.saveAs('output/playwright/hosted-chart.html');
  await page.getByRole('button', { name: /Close/i }).last().click();
  for (const width of [1440, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    await page.getByRole('textbox', { name: 'Question about your data' }).hover();
    await page.waitForTimeout(500);
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Hosted horizontal overflow at ' + width);
    await page.screenshot({ path: 'output/playwright/hosted-chat-' + width + '.png', fullPage: true });
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole('button', { name: 'Choose dataset' }).setInputFiles('output/playwright/hosted-replacement.xlsx');
  await page.getByRole('dialog').getByRole('button', { name: 'Replace dataset', exact: true }).click();
  await idle();
  assert(await page.locator('.message-assistant').count() === 0, 'XLSX replacement clears chat');
  await send('What is the total Sales across all rows?');
  assert(/\b60\b/.test(await lastAnswer()), 'Actual XLSX computation');
  await send('What name should you call me?');
  assert(!/\b(?:Sky|Asha)\b/i.test(await lastAnswer()), 'Replacement forgets prior name');
  await page.getByRole('textbox', { name: 'Question about your data' }).fill('Explain mean, median and variance in detail, with several examples.');
  await page.getByRole('button', { name: 'Send message', exact: true }).click();
  submissions++;
  await page.getByRole('button', { name: 'Stop response', exact: true }).waitFor();
  await page.getByRole('button', { name: 'Stop response', exact: true }).click();
  await idle();
  assert(await page.getByText('Stopped', { exact: true }).count() === 1, 'Hosted Stop completes once');
  assert(errors.length === 0, 'Hosted browser errors: ' + errors.join(', '));
  return { passed: true, submissions, greeting: true, nameCorrection: true, csvUpload: true, memory: true, calculation: true, chart: true, pngExport: true, htmlExport: true, xlsxReplacement: true, stop: true, reload: true, mobileWidths: [390, 320], browserErrors: errors.length };
}
