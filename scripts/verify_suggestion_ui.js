async function verifySuggestionUI(page) {
  const assert = (value, message) => {
    if (!value) throw new Error(message);
  };
  const api = "http://127.0.0.1:8001";
  const identity = await page.request.get(api + "/api/verification-fixture");
  assert(
    identity.ok() && (await identity.json()).offline_fixture === true,
    "Requires offline fixture on port 8001",
  );
  // Block before dispatch, even if the test frontend was started with the
  // wrong API setting. This script must never invoke real providers.
  const fixtureOnly = async (route) => {
    if (
      !route
        .request()
        .url()
        .startsWith(api + "/api/")
    ) {
      await route.abort("blockedbyclient");
      throw new Error(
        "Verification blocked an API outside the offline fixture",
      );
    }
    await route.continue();
  };
  await page.route("**/api/**", fixtureOnly);
  // A previous verification run can leave an editable draft. Clear only this
  // isolated test page before navigating, so its unsent-draft guard is respected.
  if (
    page.url().startsWith("http://127.0.0.1:5174/") &&
    (await page.locator("#question").isVisible())
  ) {
    await page.locator("#question").fill("");
    await page.waitForTimeout(100);
    await page.evaluate(() =>
      sessionStorage.removeItem("databuddy.session.v1"),
    );
  }
  let submissions = 0;
  const count = (request) => {
    if (
      request.url().endsWith("/api/messages") &&
      request.method() === "POST"
    ) {
      assert(
        request.url().startsWith(api + "/"),
        "Refusing non-fixture submission",
      );
      submissions++;
    }
  };
  page.on("request", count);
  const acceptUnload = async (dialog) => {
    if (dialog.type() === "beforeunload") await dialog.accept();
    else await dialog.dismiss();
  };
  page.on("dialog", acceptUnload);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("http://127.0.0.1:5174/");
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
  if (
    await page
      .getByRole("button", { name: "Try sample data", exact: true })
      .isVisible()
  )
    await page
      .getByRole("button", { name: "Try sample data", exact: true })
      .click();
  await page.waitForFunction(() => !document.querySelector(".send").disabled);
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
    await page.waitForFunction(() => !document.querySelector(".send").disabled);
  }
  if (
    await page
      .getByRole("button", { name: "Use light theme", exact: true })
      .isVisible()
  )
    await page
      .getByRole("button", { name: "Use light theme", exact: true })
      .click();
  const chart = page.getByRole("button", {
    name: "Create a chart",
    exact: true,
  });
  const menu = page.getByRole("menu", { name: "Create a chart", exact: true });
  await chart.hover();
  await menu.waitFor();
  await page.waitForTimeout(500);
  assert(await menu.isVisible(), "Hover stays open");
  const buttonBox = await chart.boundingBox();
  await page.mouse.move(buttonBox.x + buttonBox.width / 2, buttonBox.y - 3);
  await page.waitForTimeout(220);
  assert(await menu.isVisible(), "Trigger-to-menu gap stays open");
  await menu.getByRole("menuitem").first().hover();
  await menu
    .getByRole("menuitem", { name: "Total Sales by Region", exact: true })
    .click();
  await page.waitForFunction(
    () =>
      document.activeElement?.id === "question" &&
      document.querySelector("#question").value.includes('"Sales"'),
  );
  assert(submissions === 0, "Selecting never submits");
  assert(
    (await page.locator("#question").inputValue()).startsWith(
      "Create a bar chart.",
    ),
    "Complete editable chart request",
  );
  await chart.hover();
  await menu.waitFor();
  await page.mouse.move(250, 90);
  await menu.waitFor({ state: "hidden" });
  const compare = page.getByRole("button", {
    name: "Compare groups",
    exact: true,
  });
  await compare.focus();
  await compare.press("ArrowDown");
  const compareMenu = page.getByRole("menu", {
    name: "Compare groups",
    exact: true,
  });
  await compareMenu.waitFor();
  await page.keyboard.press("End");
  await page.keyboard.press("Home");
  await page.keyboard.press("r");
  await page.waitForFunction(() =>
    document.activeElement?.textContent?.startsWith("Record counts"),
  );
  await page.keyboard.press("Enter");
  await page.waitForFunction(
    () =>
      document.activeElement?.id === "question" &&
      document.querySelector("#question").value.startsWith("Compare "),
  );
  assert(submissions === 0, "Keyboard selection never submits");
  await compare.focus();
  await compare.press("ArrowDown");
  await compareMenu.waitFor();
  await page.keyboard.press("Escape");
  await compareMenu.waitFor({ state: "hidden" });
  assert(
    await compare.evaluate((el) => el === document.activeElement),
    "Escape restores trigger focus",
  );
  await compare.press("Enter");
  await compareMenu.waitFor();
  await page.keyboard.press("Escape");
  await compareMenu.waitFor({ state: "hidden" });
  await page.keyboard.press("Tab");
  const focusedMenu = page.getByRole("menu", {
    name: "Find trends",
    exact: true,
  });
  await focusedMenu.waitFor();
  assert(
    (await page.getByRole("menu").count()) === 1,
    "One menu at a time on keyboard focus",
  );
  await page.keyboard.press("Escape");
  await focusedMenu.waitFor({ state: "hidden" });
  await chart.hover();
  await menu.waitFor();
  await page.screenshot({ path: "output/playwright/suggestions-desktop.png" });
  await page.locator("#question").click();
  await menu.waitFor({ state: "hidden" });
  // Exercise the selected question through the real API/worker with provider doubles.
  await chart.hover();
  await menu.waitFor();
  await menu
    .getByRole("menuitem", { name: "Total Sales by Region", exact: true })
    .click();
  await page.waitForFunction(() => document.activeElement?.id === "question");
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  await page.locator(".progress").waitFor();
  assert(await chart.isDisabled(), "Task menus disabled while running");
  await page.locator(".progress").waitFor({ state: "hidden", timeout: 45000 });
  await page
    .locator(".chart-thumbnail .js-plotly-plot")
    .last()
    .waitFor({ timeout: 30000 });
  assert(submissions === 1, "One deliberate submission");
  await chart.hover();
  await menu
    .getByRole("menuitem", { name: "Chart the previous result", exact: true })
    .waitFor();
  await page.keyboard.press("Escape");
  if (
    await page
      .getByRole("button", { name: "Use dark theme", exact: true })
      .isVisible()
  )
    await page
      .getByRole("button", { name: "Use dark theme", exact: true })
      .click();
  await chart.hover();
  await menu.waitFor();
  await page.screenshot({ path: "output/playwright/suggestions-dark.png" });
  await page.addScriptTag({
    path: "D:/projects/databuddy 2.0/frontend/node_modules/axe-core/axe.min.js",
  });
  const violations = await page.evaluate(async () =>
    (await axe.run()).violations.map((item) => item.id),
  );
  assert(
    violations.length === 0,
    "Desktop accessibility: " + violations.join(", "),
  );
  await page.locator("#question").click();
  // Replacing the dataset must replace the suggestion set as well.
  await page
    .locator("input[type=file]")
    .setInputFiles("output/playwright/wide-suggestions.csv");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Replace dataset", exact: true })
    .click();
  await page.waitForFunction(() => !document.querySelector(".send").disabled);
  await chart.hover();
  await menu.waitFor();
  assert(
    (await menu.getByRole("menuitem").count()) === 10,
    "Exactly ten choices on wide data",
  );
  assert(
    await menu.getByText("Top 10 suggestions", { exact: true }).isVisible(),
    "Cap explained",
  );
  assert(
    !/Record ID|Previous|previous result/.test(await menu.innerText()),
    "No identifiers or stale-result choice",
  );
  await menu.getByRole("menuitem").last().click();
  await page.waitForFunction(() => document.activeElement?.id === "question");
  assert(
    (await page.locator("#question").inputValue()).length > 10,
    "Last visible choice is usable",
  );
  await page
    .locator("input[type=file]")
    .setInputFiles("output/playwright/text-suggestions.csv");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Replace dataset", exact: true })
    .click();
  await page.waitForFunction(() => !document.querySelector(".send").disabled);
  await page.getByRole("button", { name: "Find trends", exact: true }).hover();
  const trendsMenu = page.getByRole("menu", {
    name: "Find trends",
    exact: true,
  });
  await trendsMenu.waitFor();
  assert(
    (await trendsMenu.getByRole("menuitem").count()) === 0,
    "No fabricated date suggestions",
  );
  assert(
    (await trendsMenu.innerText()).includes("No usable date columns"),
    "Helpful no-date state",
  );
  await page.locator("#question").click();
  await page
    .getByRole("button", { name: "Remove dataset", exact: true })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Remove dataset", exact: true })
    .click();
  await page.waitForFunction(() => !document.querySelector(".send").disabled);
  await chart.hover();
  await page.waitForTimeout(200);
  assert(
    (await page.getByRole("menu").count()) === 0,
    "No dataset-specific menu without dataset",
  );
  assert(
    submissions === 1,
    "All later browsing and selections cost zero messages",
  );
  await page.locator("#question").fill("");
  page.off("request", count);
  page.off("dialog", acceptUnload);
  // Real touch events, a separate session, and narrow viewports.
  const touchContext = await page
    .context()
    .browser()
    .newContext({
      viewport: { width: 390, height: 844 },
      isMobile: true,
      hasTouch: true,
      deviceScaleFactor: 1,
    });
  const touch = await touchContext.newPage();
  await touch.route("**/api/**", fixtureOnly);
  await touch.goto("http://127.0.0.1:5174/");
  await touch
    .getByRole("button", { name: "Try sample data", exact: true })
    .waitFor();
  await touch.waitForFunction(() => !document.querySelector(".send").disabled);
  await touch
    .getByRole("button", { name: "Try sample data", exact: true })
    .tap();
  await touch.waitForFunction(() => !document.querySelector(".send").disabled);
  const touchChart = touch.getByRole("button", {
    name: "Create a chart",
    exact: true,
  });
  await touchChart.tap();
  const touchMenu = touch.getByRole("menu", {
    name: "Create a chart",
    exact: true,
  });
  await touchMenu.waitFor();
  for (const width of [390, 320]) {
    await touch.setViewportSize({ width, height: 844 });
    await touch.waitForTimeout(150);
    const box = await touchMenu.boundingBox();
    assert(
      box.x >= 0 && box.x + box.width <= width + 1,
      "Touch menu stays within " + width + "px",
    );
    assert(
      await touch.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      "No touch-page overflow",
    );
  }
  await touch.screenshot({ path: "output/playwright/suggestions-mobile.png" });
  await touchMenu.getByRole("menuitem").first().tap();
  await touch.waitForFunction(
    () =>
      document.activeElement?.id === "question" &&
      document
        .querySelector("#question")
        .value.startsWith("Create a bar chart."),
  );
  await touchChart.tap();
  await touchMenu.waitFor();
  await touch.locator("#question").tap();
  await touchMenu.waitFor({ state: "hidden" });
  await touchContext.close();
  await page.unroute("**/api/**", fixtureOnly);
  return "PASS: hover/gap/leave, click, keyboard, Escape, no automatic submission, deliberate end-to-end chart, busy state, persistent menus, replacement/removal, top-ten cap, no-date state, accessibility, 390/320px and real touch selection";
}
