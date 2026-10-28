import type { Dataset, SuggestionColumn } from "./types";

export type TaskId = "explore" | "chart" | "compare" | "trends" | "quality";
export type Suggestion = { label: string; prompt: string };
export type SuggestionGroup = {
  items: Suggestion[];
  limited: boolean;
  empty: string;
};
const LIMIT = 10;
const identifierName =
  /(^|[\s_\-])(id|uuid|guid|identifier|index|zip|postcode)($|[\s_\-])|postal[\s_\-]*code|row[\s_\-]*number/i;
const words = (name: string) => name.replace(/([a-z0-9])([A-Z])/g, "$1 $2");
const quote = (name: string) => JSON.stringify(name);
const aggregate = (column: SuggestionColumn) =>
  /\b(sales|revenue|profit|cost|amount|quantity|units|spend|expenses|income)\b/i.test(
    words(column.name),
  ) && !/(%|percent|rate|ratio|margin|average|mean)/i.test(column.name)
    ? "total"
    : "average";

// Stop each iterator after eleven items: enough to detect the ten-item cap.
function take(source: Iterable<Suggestion>, maximum = LIMIT + 1): Suggestion[] {
  const result: Suggestion[] = [];
  const seen = new Set<string>();
  for (const item of source) {
    if (seen.has(item.prompt) || item.prompt.length > 4000) continue;
    seen.add(item.prompt);
    result.push(item);
    if (result.length >= maximum) break;
  }
  return result;
}

function* pairs<A, B>(left: A[], right: B[]): Generator<[A, B]> {
  // Rotate dimensions so a wide dataset doesn't use every slot for one field.
  for (let offset = 0; offset < right.length; offset++) {
    for (let i = 0; i < left.length; i++)
      yield [left[i], right[(i + offset) % right.length]];
  }
}

function* interleave(...lists: Suggestion[][]): Generator<Suggestion> {
  for (let i = 0; i < Math.max(0, ...lists.map((list) => list.length)); i++) {
    for (const list of lists) if (list[i]) yield list[i];
  }
}

export function buildTaskSuggestions(
  dataset: Dataset,
): Record<TaskId, SuggestionGroup> {
  const fallback = dataset.columns.map(
    (name) =>
      ({
        name,
        kind: dataset.numeric.includes(name) ? "number" : "category",
        distinct: null,
        missing: null,
        identifier: identifierName.test(words(name)),
      }) as SuggestionColumn,
  );
  const columns = dataset.suggestion_columns ?? fallback;
  const useful = columns.filter(
    (column) =>
      !column.identifier &&
      !identifierName.test(words(column.name)) &&
      column.distinct !== 0 &&
      column.distinct !== 1,
  );
  const rank = (column: SuggestionColumn) => {
    const semantic =
      /\b(sales|revenue|profit|amount|quantity|units|score|region|category|segment|country|department|month|date)\b/i.test(
        words(column.name),
      )
        ? 2
        : 0;
    return semantic - (column.missing ?? 0) / Math.max(1, dataset.rows);
  };
  const sorted = [...useful].sort((a, b) => rank(b) - rank(a));
  const metrics = sorted.filter((column) => column.kind === "number");
  const groups = sorted.filter(
    (column) =>
      column.kind === "category" &&
      (column.distinct === null || column.distinct <= 30),
  );
  const dates = sorted.filter((column) => column.kind === "date");
  const groupCounts = take(
    (function* () {
      for (const group of groups)
        yield {
          label: `Record counts by ${group.name}`,
          prompt: `Compare the number of records for each value of ${quote(group.name)}, sorted by count.`,
        };
    })(),
  );
  const comparisons = take(
    (function* () {
      for (const [metric, group] of pairs(metrics, groups)) {
        const operation = aggregate(metric);
        yield {
          label: `${operation === "total" ? "Total" : "Average"} ${metric.name} by ${group.name}`,
          prompt: `Compare the ${operation} of ${quote(metric.name)} across the groups in ${quote(group.name)}. Show the calculated values for each group.`,
        };
      }
    })(),
  );
  const trends = take(
    (function* () {
      for (const [metric, date] of pairs(metrics, dates))
        yield {
          label: `${metric.name} over time · ${date.name}`,
          prompt: `Analyze how the ${aggregate(metric)} of ${quote(metric.name)} changes over time using ${quote(date.name)}. Use a suitable time interval and chronological order.`,
        };
      if (!metrics.length)
        for (const date of dates)
          yield {
            label: `Record counts over time · ${date.name}`,
            prompt: `Analyze how the number of records changes over time using ${quote(date.name)}. Use a suitable time interval and chronological order.`,
          };
    })(),
  );
  const distributions = metrics.map((metric) => ({
    label: `Distribution of ${metric.name}`,
    prompt: `Create a histogram showing the distribution of ${quote(metric.name)}.`,
  }));
  const chartComparisons = comparisons.map((item) => ({
    ...item,
    prompt: `Create a bar chart. ${item.prompt}`,
  }));
  const chartTrends = trends.map((item) => ({
    ...item,
    prompt: `Create a line chart. ${item.prompt}`,
  }));
  const countCharts = groupCounts.map((item) => ({
    ...item,
    prompt: `Create a bar chart. ${item.prompt}`,
  }));
  const explore = take(
    (function* () {
      yield {
        label: "Overview of this dataset",
        prompt:
          "Summarize this dataset's structure and key patterns, supported by computed results.",
      };
      yield* interleave(
        metrics.map((metric) => ({
          label: `Summarize ${metric.name}`,
          prompt: `Summarize ${quote(metric.name)} with its count, minimum, maximum, average and missing values.`,
        })),
        groupCounts,
      );
    })(),
  );
  const quality = take(
    (function* () {
      yield {
        label: "Overall data quality",
        prompt:
          "Check this dataset for missing values, duplicate rows and data quality issues. Report computed counts.",
      };
      yield {
        label: "Missing values by column",
        prompt:
          "Count missing values and their percentages in every column, sorted from most to least missing.",
      };
      yield {
        label: "Duplicate rows",
        prompt:
          "Count duplicate rows in this dataset and explain how duplicates were identified.",
      };
      for (const column of [...columns].sort(
        (a, b) => (b.missing ?? 0) - (a.missing ?? 0),
      )) {
        if (column.missing)
          yield {
            label: `Missing values in ${column.name}`,
            prompt: `Check missing values in ${quote(column.name)} and report the count and percentage.`,
          };
      }
      for (const column of columns.filter((column) => column.identifier))
        yield {
          label: `Check ${column.name}`,
          prompt: `Check ${quote(column.name)} for missing or repeated identifiers. Report computed counts without printing individual values.`,
        };
      for (const metric of metrics)
        yield {
          label: `Unusual values in ${metric.name}`,
          prompt: `Check ${quote(metric.name)} for potential outliers. Explain the method and report counts without treating outliers as confirmed errors.`,
        };
    })(),
  );
  const group = (items: Suggestion[], empty: string): SuggestionGroup => ({
    items: items.slice(0, LIMIT),
    limited: items.length > LIMIT,
    empty,
  });
  return {
    explore: group(explore, "Ask a question about your dataset."),
    chart: group(
      take(
        interleave(chartComparisons, chartTrends, distributions, countCharts),
      ),
      "No suitable numeric, date or grouped columns were found. You can still type your own chart request.",
    ),
    compare: group(
      take(interleave(comparisons, groupCounts)),
      "No suitable group columns were found. You can still type your own comparison.",
    ),
    trends: group(
      trends,
      "No usable date columns were detected. You can still ask about an ordered field in your own words.",
    ),
    quality: group(quality, "Ask about data quality in your own words."),
  };
}
