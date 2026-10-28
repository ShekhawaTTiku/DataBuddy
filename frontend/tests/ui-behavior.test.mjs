import assert from "node:assert/strict";
import { test } from "node:test";
import { chartGeometry, readableLayout } from "../src/chartLayout.ts";
import { readPreferences, savePreferences } from "../src/preferences.ts";

const dashboard = {
  data: [],
  layout: {
    height: 600,
    title: { text: "Sales overview" },
    xaxis: { domain: [0, 0.45], title: { text: "Month" } },
    xaxis2: { domain: [0.55, 1] },
    xaxis3: { domain: [0, 0.45] },
    xaxis4: { domain: [0.55, 1] },
    yaxis: { domain: [0.575, 1] },
    yaxis2: { domain: [0.575, 1] },
    yaxis3: { domain: [0, 0.425] },
    yaxis4: { domain: [0, 0.425] },
  },
};

test("four-panel charts keep readable height and minimum width, including previews", () => {
  const before = structuredClone(dashboard);
  const geometry = chartGeometry(dashboard);
  assert.equal(geometry.panels, 4);
  assert.ok(geometry.width >= 1100);
  assert.ok(geometry.height >= 780);
  for (const preview of [false, true]) {
    const layout = readableLayout(dashboard, true, preview);
    assert.ok(layout.height >= 780);
    assert.equal(layout.title.text, "Sales overview");
    assert.equal(layout.xaxis.title.text, "Month");
    assert.equal(layout.xaxis.automargin, true);
    assert.ok(layout.margin.t >= 130);
    assert.equal(layout.legend.orientation, "h");
  }
  assert.deepEqual(dashboard, before);
});

test("single charts and overlay axes do not become a dashboard", () => {
  const figure = {
    data: [],
    layout: { height: 700, yaxis2: { overlaying: "y" } },
  };
  assert.equal(chartGeometry(figure).dashboard, false);
  assert.equal(readableLayout(figure, false).height, 700);
  assert.equal(readableLayout(figure, false, true).height, 300);
});

test("display preferences are allowlisted and tolerate malformed or unavailable storage", () => {
  let stored =
    '{"dark":true,"sidebar":false,"analysisTab":"Calculation","question":"discard me"}';
  globalThis.localStorage = {
    getItem: () => stored,
    setItem: (_, value) => {
      stored = value;
    },
  };
  const preferences = readPreferences();
  assert.deepEqual(preferences, {
    dark: true,
    sidebar: false,
    analysisTab: "Calculation",
  });
  savePreferences(preferences);
  assert.equal(stored.includes("question"), false);
  stored = '{"dark":"true","sidebar":0,"analysisTab":"unknown"}';
  assert.deepEqual(readPreferences(), {
    dark: false,
    sidebar: true,
    analysisTab: "Chart",
  });
  stored = "malformed";
  assert.equal(readPreferences().analysisTab, "Chart");
  globalThis.localStorage = {
    getItem: () => {
      throw Error();
    },
    setItem: () => {
      throw Error();
    },
  };
  assert.equal(readPreferences().dark, false);
  assert.doesNotThrow(() => savePreferences(preferences));
});
