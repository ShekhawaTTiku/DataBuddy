async function verifyStreamingUI(page) {
  // Suppress the existing unsaved-work confirmation only in this test page.
  // The reload still exercises a new React instance attaching to the same job.
  await page.addInitScript(() => {
    const original = window.addEventListener;
    window.addEventListener = function (type, ...args) {
      if (type !== "beforeunload") original.call(this, type, ...args);
    };
  });
  const assert = (value, message) => {
    if (!value) throw new Error(message);
  };
  const api = "http://127.0.0.1:8001";
  const identity = await page.request.get(api + "/api/verification-fixture");
  assert(
    identity.ok() && (await identity.json()).offline_fixture === true,
    "Requires offline streaming fixture",
  );
  assert(
    new URL(page.url()).port === "5174",
    "Requires isolated frontend on port 5174",
  );
  await page.route("**/api/**", async (route) => {
    assert(
      route
        .request()
        .url()
        .startsWith(api + "/api/"),
      "Refusing a non-fixture API",
    );
    await route.continue();
  });
  let submissions = 0;
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().endsWith("/api/messages"))
      submissions++;
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.evaluate(() => {
    sessionStorage.clear();
  });
  await page.reload();
  await page
    .getByRole("button", { name: "Try sample data", exact: true })
    .click();
  const send = async (question) => {
    await page
      .getByRole("textbox", { name: "Question about your data" })
      .fill(question);
    await page
      .getByRole("button", { name: "Send message", exact: true })
      .click();
  };
  const idle = () =>
    page.waitForFunction(() => {
      const button = document.querySelector('[aria-label="Send message"]');
      return button && !button.disabled;
    });
  await idle();
  await send("Total sales?");
  await page
    .getByRole("button", { name: "Result data", exact: true })
    .last()
    .waitFor();
  const snapshots = new Set();
  let memoryVisible = false;
  for (let i = 0; i < 80; i++) {
    snapshots.add(
      await page
        .locator(".message-assistant .prose")
        .last()
        .textContent()
        .catch(() => ""),
    );
    if (
      (
        await page
          .locator(".progress")
          .textContent()
          .catch(() => "")
      ).includes("Updating session memory")
    )
      memoryVisible = true;
    if (
      await page
        .getByRole("button", { name: "Send message", exact: true })
        .isEnabled()
        .catch(() => false)
    )
      break;
    await page.waitForTimeout(50);
  }
  assert(
    [...snapshots].filter(Boolean).length >= 2,
    "Answer grows before job completion",
  );
  assert(memoryVisible, "Answer remains visible during memory update");
  await idle();
  await send("Hello slow streaming reconnect");
  await page
    .locator(".message-assistant")
    .last()
    .getByText("Hello!", { exact: false })
    .waitFor();
  await page.reload();
  await idle();
  assert(submissions === 2, "Reload attaches without resubmitting");
  assert(
    (await page.locator("article.exchange").count()) === 2,
    "One exchange per submitted request after reload",
  );
  await send("Hello slow streaming stop");
  await page
    .getByRole("button", { name: "Stop response", exact: true })
    .waitFor();
  await page.waitForTimeout(350);
  await page
    .getByRole("button", { name: "Stop response", exact: true })
    .click();
  await idle();
  assert(
    (await page.getByText("Stopped", { exact: true }).count()) === 1,
    "One stopped exchange",
  );
  assert(submissions === 3, "Stop does not resubmit");
  await send("Total sales with fallback");
  await page
    .locator(".message-assistant")
    .last()
    .getByText("An unfinished primary explanation", { exact: false })
    .waitFor();
  await idle();
  const recovered = await page
    .locator(".message-assistant")
    .last()
    .textContent();
  assert(
    recovered.includes("Backup explanation") &&
      !recovered.includes("unfinished primary"),
    "Fallback replaces the draft",
  );
  await send("Create a chart of Sales by Region");
  await page
    .getByRole("button", { name: "Open interactive chart", exact: false })
    .last()
    .waitFor();
  const chartDuringWork =
    (await page
      .getByRole("button", { name: "Stop response", exact: true })
      .count()) > 0;
  assert(chartDuringWork, "Chart is delivered before narration completes");
  await idle();
  await page
    .getByRole("button", { name: "Open interactive chart", exact: false })
    .last()
    .click();
  await page.getByRole("dialog").waitFor();
  await page.getByRole("button", { name: "Close panel", exact: true }).click();
  await page.screenshot({ path: "output/playwright/streaming-desktop.png" });
  assert(
    (await page.locator("article.exchange").count()) === 5 && submissions === 5,
    "Final exchanges match admissions",
  );
  await page
    .getByRole("button", { name: "Use dark theme", exact: true })
    .click();
  await page.screenshot({ path: "output/playwright/streaming-dark.png" });
  await page.setViewportSize({ width: 390, height: 844 });
  await send("Hello slow mobile stop");
  await page
    .getByRole("button", { name: "Stop response", exact: true })
    .waitFor();
  await page
    .getByRole("button", { name: "Stop response", exact: true })
    .click();
  await idle();
  assert(
    (await page.getByText("Stopped", { exact: true }).count()) === 2 &&
      submissions === 6,
    "Mobile Stop settles once",
  );
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
      "No mobile page overflow",
    );
  }
  await page.screenshot({ path: "output/playwright/streaming-mobile.png" });
  await page.addScriptTag({
    path: "D:/projects/databuddy 2.0/frontend/node_modules/axe-core/axe.min.js",
  });
  const violations = await page.evaluate(async () =>
    (await axe.run()).violations.map((item) => item.id),
  );
  assert(violations.length === 0, "Accessibility: " + violations.join(", "));
  assert(errors.length === 0, "No browser errors: " + errors.join(", "));
  return {
    incrementalStates: snapshots.size,
    submissions,
    reconnect: true,
    stopped: true,
    chartBeforeNarration: true,
    mobileWidths: [390, 320],
    axeViolations: violations.length,
  };
}
