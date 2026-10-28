import assert from "node:assert/strict";
import { test } from "node:test";
import { buildTaskSuggestions } from "../src/suggestionBuilder.ts";

const column = (name, kind, distinct = 3, extra = {}) => ({
  name,
  kind,
  distinct,
  missing: 0,
  identifier: false,
  ...extra,
});
const dataset = (columns) => ({
  filename: "synthetic.csv",
  rows: 100,
  columns: columns.map((c) => c.name),
  numeric: columns.filter((c) => c.kind === "number").map((c) => c.name),
  categories: columns.filter((c) => c.kind === "category").map((c) => c.name),
  preview: [],
  warnings: [],
  suggestion_columns: columns,
});

test("complete suggestions use real fields, safe aggregations and actual dates", () => {
  const data = dataset([
    column("Order Date", "date"),
    column("Region", "category"),
    column("Sales", "number"),
    column("Profit Margin", "number"),
    column("CustomerID", "number", 100, { identifier: true }),
    column("Empty", "number", 0),
    column("Constant", "number", 1),
  ]);
  const before = structuredClone(data);
  const result = buildTaskSuggestions(data);
  assert.ok(
    result.chart.items.some((item) => item.prompt.includes('total of "Sales"')),
  );
  assert.ok(
    result.compare.items.some((item) =>
      item.prompt.includes('average of "Profit Margin"'),
    ),
  );
  assert.ok(
    result.trends.items.every((item) => item.prompt.includes('"Order Date"')),
  );
  for (const id of ["chart", "compare", "trends"]) {
    for (const item of result[id].items) {
      assert.ok(!/CustomerID|Empty|Constant/.test(item.prompt));
      assert.ok(item.prompt.endsWith("."));
      assert.ok(item.label.length > 0);
    }
  }
  assert.ok(
    result.quality.items.some((item) => item.prompt.includes('"CustomerID"')),
  );
  assert.deepEqual(data, before);
});

test("wide datasets have at most ten unique choices with varied metrics", () => {
  const data = dataset([
    ...Array.from({ length: 35 }, (_, i) => column("Metric " + i, "number")),
    column("Region", "category"),
    column("Category", "category"),
    column("Date", "date"),
  ]);
  const result = buildTaskSuggestions(data);
  for (const group of Object.values(result)) {
    assert.ok(group.items.length <= 10);
    assert.equal(
      new Set(group.items.map((item) => item.prompt)).size,
      group.items.length,
    );
  }
  assert.equal(result.chart.limited, true);
  assert.equal(result.compare.limited, true);
  assert.ok(
    result.compare.items.some((item) => item.prompt.includes("Metric 1")),
  );
  assert.deepEqual(result, buildTaskSuggestions(data));
});

test("no dates, all-text, date-only, constant-only and numeric-only datasets stay honest", () => {
  const text = buildTaskSuggestions(
    dataset([column("Region", "category"), column("Notes", "text", 100)]),
  );
  assert.ok(
    text.chart.items.some((item) => item.label.includes("Record counts")),
  );
  assert.equal(text.trends.items.length, 0);
  assert.match(text.trends.empty, /No usable date/);
  assert.ok(!JSON.stringify(text.chart).includes("Notes"));
  const numbers = buildTaskSuggestions(dataset([column("Score", "number")]));
  assert.equal(numbers.compare.items.length, 0);
  assert.match(numbers.chart.items[0].prompt, /histogram/);
  const date = buildTaskSuggestions(dataset([column("Date", "date")]));
  assert.match(date.trends.items[0].prompt, /number of records/);
  assert.equal(
    buildTaskSuggestions(dataset([column("Empty", "number", 0)])).chart.items
      .length,
    0,
  );
});

test("untrusted names remain exact quoted text and overly long prompts are not offered", () => {
  const name = 'Sales "quoted" <script>';
  const result = buildTaskSuggestions(
    dataset([
      column(name, "number"),
      column("Region", "category"),
      column("x".repeat(4100), "number"),
    ]),
  );
  assert.ok(
    result.compare.items.some((item) =>
      item.prompt.includes(JSON.stringify(name)),
    ),
  );
  assert.ok(
    Object.values(result).every((group) =>
      group.items.every((item) => item.prompt.length <= 4000),
    ),
  );
});
