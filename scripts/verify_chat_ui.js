async function verifyChatUI(page) {
  const assert = (value, message) => { if (!value) throw new Error(message); };
  const fixture = await page.request.get('http://127.0.0.1:8001/api/verification-fixture');
  assert(fixture.ok() && (await fixture.json()).offline_fixture, 'Requires the offline browser fixture');
  assert(new URL(page.url()).port === '5174', 'Requires the isolated local frontend');
  await page.addInitScript(() => {
    const original = window.addEventListener;
    window.addEventListener = function(type, ...args) {
      if (type !== 'beforeunload') original.call(this, type, ...args);
    };
  });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.evaluate(() => sessionStorage.clear());
  await page.reload();
  await page.getByRole('button', { name: 'Send message', exact: true }).waitFor();
  const idle = () => page.waitForFunction(() => {
    const send = document.querySelector('[aria-label="Send message"]');
    return send && !send.disabled;
  });
  const send = async text => {
    await idle();
    const before = await page.locator('.message-assistant').count();
    await page.getByRole('textbox', { name: 'Question about your data' }).fill(text);
    await page.getByRole('button', { name: 'Send message', exact: true }).click();
    await page.waitForFunction(count => document.querySelectorAll('.message-assistant').length > count, before);
    await idle();
  };
  const lastAnswer = () => page.locator('.message-assistant .prose').last().textContent();
  await send('Hi, my name is Mira');
  assert((await lastAnswer()).includes('Hi Mira'), 'Greeting before upload');
  await send("What's my name?");
  assert((await lastAnswer()).includes('Mira'), 'Name recalled before upload');
  await page.reload();
  await idle();
  assert((await lastAnswer()).includes('Mira'), 'Chat restored after reload');
  await send('Hi, calculate total sales');
  assert((await lastAnswer()).includes('Upload your CSV'), 'Mixed greeting requests data without invented results');
  await send('provider failure');
  assert((await lastAnswer()).includes('unavailable'), 'Provider failure is visible');
  await send('Hello again');
  const beforeUpload = await page.locator('.message-assistant').count();
  await page.getByRole('button', { name: 'Try sample data', exact: true }).click();
  await idle();
  assert(await page.locator('.message-assistant').count() === beforeUpload, 'First upload preserves chat');
  await send("What's my name?");
  assert((await lastAnswer()).includes('Mira'), 'Name recalled after first upload');
  await send('Total sales?');
  await page.getByRole('button', { name: 'Result data', exact: true }).last().waitFor();
  assert((await lastAnswer()).includes('1000'), 'Data analysis after chat');
  await send('Make a sales chart');
  await page.getByRole('button', { name: 'Open interactive chart', exact: false }).last().waitFor();
  await page.setViewportSize({ width: 320, height: 780 });
  await page.screenshot({ path: 'output/playwright/chat-mobile.png', fullPage: true });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Mobile page has no horizontal overflow');
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({ path: 'output/playwright/chat-desktop.png', fullPage: true });
  await page.getByRole('button', { name: 'Clear chat', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Clear chat', exact: true }).click();
  await idle();
  assert(await page.locator('.message-assistant').count() === 0, 'Clear chat resets conversation');
  await page.getByRole('button', { name: 'Remove dataset', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Remove dataset', exact: true }).click();
  await idle();
  await send("What's my name?");
  assert(!(await lastAnswer()).includes('Mira'), 'Removed dataset clears remembered introduction');
  assert(errors.length === 0, 'No browser exceptions: ' + errors.join(', '));
  return { passed: true, checks: ['greetings', 'name recall', 'reload', 'mixed request', 'provider failure/recovery', 'first upload', 'calculation', 'chart', 'mobile', 'clear/remove'] };
}
