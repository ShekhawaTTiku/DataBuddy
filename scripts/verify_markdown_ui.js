async function verifyMarkdownUI(page) {
  const assert = (value, message) => { if (!value) throw new Error(message); };
  assert(new URL(page.url()).origin === 'http://127.0.0.1:5174', 'Requires isolated local frontend');
  const identity = await page.request.get('http://127.0.0.1:8001/api/verification-fixture');
  assert(identity.ok() && (await identity.json()).offline_fixture === true, 'Requires offline provider fixture');
  const guard = async route => {
    assert(route.request().url() === 'http://127.0.0.1:8001/api/messages', 'Refusing non-fixture inference');
    await route.continue();
  };
  await page.route('**/api/messages', guard);
  await page.getByRole('button', {name:'Try sample data',exact:true}).click();
  await page.getByRole('textbox', {name:'Question about your data'}).fill('wide markdown');
  await page.getByRole('button', {name:'Send message',exact:true}).click();
  const table = page.getByRole('table', {name:'Response table',exact:true});
  await table.waitFor();
  await page.waitForFunction(() => {
    const send = document.querySelector('[aria-label="Send message"]');
    return send && !send.disabled;
  });
  await page.unroute('**/api/messages', guard);
  for (const width of [390,320]) {
    await page.setViewportSize({width,height:900});
    await table.evaluate(element => { element.scrollLeft = 0; });
    await table.focus();
    assert(await table.evaluate(element => element === document.activeElement && element.tabIndex === 0), 'Response table must accept keyboard focus');
    assert(await table.evaluate(element => element.scrollWidth > element.clientWidth), 'Synthetic table must overflow for this check');
    await page.keyboard.press('ArrowRight');
    await page.waitForTimeout(250);
    assert(await table.evaluate(element => element.scrollLeft > 0), 'Arrow key must scroll the focused table');
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'No page overflow');
  }
  return {passed:true,widths:[390,320],keyboardFocus:true,keyboardScroll:true,providerCalls:0};
}
