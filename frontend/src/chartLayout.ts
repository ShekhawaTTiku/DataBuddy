import type { Data, Layout } from "plotly.js";

export type Figure = { data: Data[]; layout: Partial<Layout> };
type Axis = {
  domain?: number[];
  title?: { text?: string; standoff?: number };
  [key: string]: unknown;
};

export function chartGeometry(figure: Figure) {
  const entries = Object.entries(figure.layout || {});
  const domains = (prefix: string) =>
    new Set(
      entries
        .filter(
          ([name, axis]) =>
            new RegExp(`^${prefix}axis[0-9]*$`).test(name) &&
            (axis as Axis)?.domain,
        )
        .map(([, axis]) =>
          (axis as Axis).domain!.map((v) => v.toFixed(3)).join(","),
        ),
    ).size;
  const columns = Math.max(1, domains("x"));
  const rows = Math.max(1, domains("y"));
  const domainPanels = figure.data.filter((trace) => "domain" in trace).length;
  const panels = Math.max(columns * rows, domainPanels, 1);
  const dashboard = panels > 1;
  const width = dashboard
    ? Math.max(
        960,
        columns * 490 + 160,
        Math.min(1600, figure.layout.width || 0),
      )
    : 0;
  const height = Math.max(
    dashboard ? rows * 300 + 180 : 500,
    Math.min(1800, figure.layout.height || 0),
  );
  return { dashboard, panels, width, height };
}

export function readableLayout(
  figure: Figure,
  dark: boolean,
  preview = false,
): Partial<Layout> {
  const geometry = chartGeometry(figure);
  const layout: Partial<Layout> = {
    ...figure.layout,
    autosize: true,
    width: undefined,
    height: geometry.height,
    paper_bgcolor: dark ? "#222A27" : "#FFFFFF",
    plot_bgcolor: dark ? "#222A27" : "#FFFFFF",
    font: {
      ...figure.layout.font,
      family: "DM Sans, sans-serif",
      size: 13,
      color: dark ? "#F2F3ED" : "#252824",
    },
    margin: {
      l: Math.max(75, figure.layout.margin?.l || 0),
      r: Math.max(geometry.dashboard ? 115 : 55, figure.layout.margin?.r || 0),
      t: Math.max(geometry.dashboard ? 130 : 100, figure.layout.margin?.t || 0),
      b: Math.max(85, figure.layout.margin?.b || 0),
    },
    title: {
      ...figure.layout.title,
      x: 0.02,
      xanchor: "left",
      y: 0.98,
      yanchor: "top",
      font: { size: 18 },
    },
    legend: {
      ...figure.layout.legend,
      orientation: "h",
      x: 0,
      xanchor: "left",
      y: 1.09,
      yanchor: "bottom",
      font: { size: 12 },
    },
  };
  for (const [name, value] of Object.entries(figure.layout)) {
    if (!/^[xy]axis[0-9]*$/.test(name)) continue;
    const axis = value as Axis;
    Object.assign(layout, {
      [name]: {
        ...axis,
        automargin: true,
        tickfont: { size: 12 },
        title: {
          ...(typeof axis.title === "string"
            ? { text: axis.title }
            : axis.title),
          standoff: 16,
          font: { size: 13 },
        },
      },
    });
  }
  // Single-chart previews stay compact; dashboards retain their panel geometry.
  if (preview && !geometry.dashboard) {
    layout.height = 300;
    layout.title = { text: "" };
    layout.showlegend = false;
    layout.margin = { l: 65, r: 45, t: 25, b: 65 };
  }
  return layout;
}
