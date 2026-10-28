async function verifyWebUI(page) {
  const assert = (value, message) => {
    if (!value) throw new Error(message);
  };
  // Run through playwright-cli against scripts/browser_fixture.py only.
  const identity = await page.request.get(
    new URL("/api/verification-fixture", page.url()).href,
  );
  assert(
    identity.ok() && (await identity.json()).offline_fixture === true,
    "Requires the offline browser fixture; refusing to send questions",
  );
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.reload();
  await page.waitForFunction(
    () =>
      !document.querySelector(".send").disabled ||
      document.body.textContent.includes("Start new session"),
  );
  if (
    await page
      .getByRole("button", { name: "Start new session", exact: true })
      .isVisible()
  )
    await page
      .getByRole("button", { name: "Start new session", exact: true })
      .click();
  await page.waitForFunction(() => !document.querySelector(".send").disabled);
  assert(
    await page
      .locator("#question")
      .evaluate((el) => el === document.activeElement),
    "Initial input focus",
  );
  if (
    await page
      .getByRole("button", { name: "Show sidebar", exact: true })
      .isVisible()
  )
    await page
      .getByRole("button", { name: "Show sidebar", exact: true })
      .click();
  if (
    await page
      .getByRole("button", { name: "Use light theme", exact: true })
      .isVisible()
  )
    await page
      .getByRole("button", { name: "Use light theme", exact: true })
      .click();
  const usage = page.getByRole("button", {
    name: "Session usage",
    exact: true,
  });
  await usage.hover();
  const box = await usage.boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height + 2);
  await page.waitForTimeout(240);
  assert(
    await page
      .getByRole("region", { name: "Session usage details" })
      .isVisible(),
    "Hover bridge stays open",
  );
  await page.getByRole("region", { name: "Session usage details" }).hover();
  await page.getByText("Limits and estimates", { exact: true }).click();
  assert(
    await page.getByText("Limits are shared", { exact: false }).isVisible(),
    "Usage details reachable",
  );
  await page.mouse.move(600, 300);
  await page.waitForTimeout(250);
  assert(
    !(await page
      .getByRole("region", { name: "Session usage details" })
      .isVisible()),
    "Usage closes outside",
  );
  if (
    await page
      .getByRole("button", { name: "Try sample data", exact: true })
      .isVisible()
  )
    await page
      .getByRole("button", { name: "Try sample data", exact: true })
      .click();
  if (
    await page
      .getByRole("button", { name: "Clear chat", exact: true })
      .isEnabled()
  ) {
    await page.getByRole("button", { name: "Clear chat", exact: true }).click();
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Clear chat", exact: true })
      .click();
  }
  await page
    .getByRole("button", { name: "Preview dataset", exact: true })
    .first()
    .waitFor();
  let delayed = false;
  await page.route(
    "**/api/messages",
    async (route) => {
      const response = await route.fetch();
      assert(
        await page.locator(".progress").isVisible(),
        "Loading appears before request acknowledgement",
      );
      await page.waitForTimeout(500);
      await route.fulfill({ response });
    },
    { times: 1 },
  );
  await page.route(
    "**/api/session",
    async (route) => {
      const response = await route.fetch();
      delayed = true;
      await page.waitForTimeout(500);
      assert(
        await page.locator(".progress").isVisible(),
        "Loading remains while completed content is in transit",
      );
      await route.fulfill({ response });
    },
    { times: 1 },
  );
  await page.locator("#question").fill("markdown formatting and long answer");
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  await page.locator(".progress").waitFor();
  await page.locator(".progress").waitFor({ state: "hidden", timeout: 45000 });
  await page.locator(".katex").first().waitFor({ timeout: 30000 });
  assert(delayed, "Delayed content loading check ran");
  await page.waitForFunction(() => {
    const el = document.querySelector(".conversation-scroll");
    return el.scrollHeight - el.scrollTop - el.clientHeight < 5;
  });
  const initialBottom = await page
    .locator(".conversation-scroll")
    .evaluate((el) => el.scrollHeight - el.scrollTop - el.clientHeight);
  assert(initialBottom < 5, "Initial answer follows bottom");
  await page
    .locator('[data-streamdown="mermaid-block"]')
    .first()
    .scrollIntoViewIfNeeded();
  await page.locator('svg[id^="mermaid-"]').first().waitFor({ timeout: 30000 });
  await page.screenshot({ path: "output/playwright/markdown-desktop.png" });
  await page
    .getByRole("button", { name: "Latest message", exact: true })
    .click();
  await page.waitForFunction(() => {
    const el = document.querySelector(".conversation-scroll");
    return el.scrollHeight - el.scrollTop - el.clientHeight < 5;
  });
  assert((await page.locator(".prose table").count()) >= 1, "GFM table");
  const blocks = await page
    .locator("[data-streamdown]")
    .evaluateAll((els) => [...new Set(els.map((el) => el.dataset.streamdown))]);
  console.log(JSON.stringify({ markdownBlocks: blocks }));
  await page.waitForTimeout(800);
  const scroll = page.locator(".conversation-scroll");
  let position = await scroll.evaluate((el) => ({
    top: el.scrollTop,
    remaining: el.scrollHeight - el.scrollTop - el.clientHeight,
  }));
  assert(position.remaining < 5, "Initial answer follows bottom");
  const bounds = await scroll.boundingBox();
  await page.mouse.move(bounds.x + 8, bounds.y + 100);
  await page.mouse.wheel(0, -1000);
  await page.waitForFunction(
    (before) =>
      document.querySelector(".conversation-scroll").scrollTop < before - 300,
    position.top,
  );
  const away = await scroll.evaluate((el) => el.scrollTop);
  assert(away < position.top - 300, "Scroll works over outer gutter");
  await page
    .getByRole("button", { name: "Latest message", exact: true })
    .waitFor();
  await page.locator("#question").fill("Create a chart dashboard");
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  await page.locator(".progress").waitFor({ state: "hidden", timeout: 45000 });
  await page
    .locator(".chart-thumbnail .js-plotly-plot")
    .waitFor({ timeout: 30000 });
  await page.waitForTimeout(1000);
  assert(
    Math.abs((await scroll.evaluate((el) => el.scrollTop)) - away) < 40,
    "New result respects scroll breakaway",
  );
  await page
    .getByRole("button", { name: "Latest message", exact: true })
    .click();
  await page.waitForFunction(() => {
    const el = document.querySelector(".conversation-scroll");
    return el.scrollHeight - el.scrollTop - el.clientHeight < 5;
  });
  assert(
    (await scroll.evaluate(
      (el) => el.scrollHeight - el.scrollTop - el.clientHeight,
    )) < 5,
    "Jump resumes following",
  );
  await page.getByRole("button", { name: /Open interactive chart/ }).click();
  await page.getByRole("dialog", { name: "Analysis", exact: true }).waitFor();
  await page
    .getByRole("region", { name: "Interactive chart", exact: true })
    .locator(".js-plotly-plot")
    .waitFor();
  const charts = await page
    .locator(".js-plotly-plot")
    .evaluateAll((els) =>
      els.map((el) => ({
        width: el._fullLayout.width,
        height: el._fullLayout.height,
        panels: el._fullLayout._subplots.cartesian.length,
      })),
    );
  console.log(JSON.stringify({ charts }));
  assert(
    charts.every(
      (chart) =>
        chart.width >= 960 && chart.height >= 780 && chart.panels === 4,
    ),
    "Dashboard retains readable geometry",
  );
  await page.screenshot({ path: "output/playwright/dashboard-desktop.png" });
  await page.evaluate(() => {
    window.__originalObjectURL = URL.createObjectURL;
    URL.createObjectURL = (blob) => {
      window.__exportedBlob = blob;
      return window.__originalObjectURL(blob);
    };
  });
  for (const [button, file] of [
    ["Download PNG", "chart.png"],
    ["Download HTML", "chart.html"],
  ]) {
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: button, exact: true }).click(),
    ]);
    await download.saveAs("output/playwright/" + file);
    assert((await download.failure()) === null, button + " succeeds");
    if (button === "Download HTML") {
      const exported = await page.context().newPage();
      const html = await page.evaluate(() => window.__exportedBlob.text());
      await exported.setContent(html);
      await exported.locator(".js-plotly-plot").waitFor();
      assert(
        (await exported.locator("script[src]").count()) === 0,
        "HTML export is self-contained",
      );
      assert(
        await exported
          .locator(".js-plotly-plot")
          .evaluate((el) => el.clientHeight >= 780),
        "HTML export keeps dashboard height",
      );
      await exported.close();
    }
  }
  await page.evaluate(() => {
    URL.createObjectURL = window.__originalObjectURL;
    delete window.__originalObjectURL;
    delete window.__exportedBlob;
  });
  await page.getByRole("dialog").evaluate((el) => (el.scrollTop = 0));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(500);
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    "No mobile page overflow",
  );
  const viewport = page.getByRole("region", {
    name: "Interactive chart",
    exact: true,
  });
  assert(
    await viewport.evaluate((el) => el.scrollWidth > el.clientWidth),
    "Mobile chart has horizontal scroll",
  );
  assert(
    await viewport
      .locator(".js-plotly-plot")
      .evaluate((el) => el.clientHeight >= 780),
    "Mobile resize preserves chart height",
  );
  await viewport.evaluate((el) => (el.scrollLeft = el.scrollWidth));
  await page.screenshot({ path: "output/playwright/dashboard-mobile.png" });
  await page.getByRole("button", { name: "Close panel", exact: true }).click();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page
    .getByRole("button", { name: "Use dark theme", exact: true })
    .click();
  await page.getByRole("button", { name: "Hide sidebar", exact: true }).click();
  await page.reload();
  await page.waitForFunction(() => !document.querySelector(".send").disabled);
  assert(
    await page.evaluate(
      () => document.documentElement.dataset.theme === "dark",
    ),
    "Theme survives reload",
  );
  assert(
    await page
      .getByRole("button", { name: "Show sidebar", exact: true })
      .isVisible(),
    "Sidebar preference survives reload",
  );
  await page
    .locator(".chart-thumbnail .js-plotly-plot")
    .waitFor({ timeout: 30000 });
  await page.waitForFunction(() => {
    const el = document.querySelector(".conversation-scroll");
    return el.scrollHeight - el.scrollTop - el.clientHeight < 5;
  });
  await page.getByRole("button", { name: "Show sidebar", exact: true }).click();
  await page.getByRole("button", { name: "Clear chat", exact: true }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Clear chat", exact: true })
    .click();
  await page.waitForFunction(() => document.activeElement?.id === "question");
  return "PASS: usage hover, formatting, outer scrolling, breakaway, dashboards, PNG/HTML exports, responsive sizing, preferences, reload, reset autofocus, delayed content loading";
}
