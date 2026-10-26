import { memo, useRef, useState } from "react";
import createPlotlyComponent from "react-plotly.js/factory";
import Plotly from "plotly.js-dist-min";
import type { Layout, Data } from "plotly.js";
const Plot = createPlotlyComponent(Plotly);

export const ChartThumbnail = memo(function ChartThumbnail({
  json,
  dark,
}: {
  json: string;
  dark: boolean;
}) {
  const figure = JSON.parse(json) as { data: Data[]; layout: Partial<Layout> };
  return (
    <div className="chart-thumbnail" aria-hidden="true">
      <Plot
        data={figure.data}
        layout={{
          ...figure.layout,
          autosize: true,
          width: undefined,
          height: 180,
          title: { text: "" },
          showlegend: false,
          margin: { l: 45, r: 15, t: 15, b: 35 },
          paper_bgcolor: dark ? "#222A27" : "#FFFFFF",
          plot_bgcolor: dark ? "#222A27" : "#FFFFFF",
          font: {
            family: "DM Sans, sans-serif",
            color: dark ? "#F2F3ED" : "#252824",
            size: 10,
          },
        }}
        config={{ staticPlot: true, responsive: true, displayModeBar: false }}
        useResizeHandler
        style={{ width: "100%" }}
      />
    </div>
  );
});

export default function Chart({
  json,
  description,
  dark,
}: {
  json: string;
  description: string;
  dark: boolean;
}) {
  const graph = useRef<HTMLElement | null>(null);
  const [error, setError] = useState("");
  const figure = JSON.parse(json) as { data: Data[]; layout: Partial<Layout> };
  const layout: Partial<Layout> = {
    ...figure.layout,
    autosize: true,
    width: undefined,
    height: 360,
    paper_bgcolor: dark ? "#222A27" : "#FFFFFF",
    plot_bgcolor: dark ? "#222A27" : "#FFFFFF",
    font: {
      ...figure.layout?.font,
      family: "DM Sans, sans-serif",
      color: dark ? "#F2F3ED" : "#252824",
    },
    margin: { l: 55, r: 25, t: 55, b: 65 },
  };
  async function png() {
    try {
      if (graph.current)
        await Plotly.downloadImage(graph.current, {
          format: "png",
          filename: "databuddy-chart",
          width: 1200,
          height: 800,
        });
    } catch {
      setError("The chart could not be exported. Try again.");
    }
  }
  async function html() {
    try {
      // Bundle the installed Plotly source into a self-contained offline export.
      const { default: sourceUrl } =
        await import("plotly.js-dist-min/plotly.min.js?url");
      const source = await fetch(sourceUrl).then((r) => {
        if (!r.ok) throw Error();
        return r.text();
      });
      const data = JSON.stringify({
        data: figure.data,
        layout: figure.layout,
      }).replace(/</g, "\\u003c");
      const blob = new Blob(
        [
          `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DataBuddy chart</title><div id="chart"></div><script>${source.replace(/<\/script/gi, "<\\/script")}</script><script>const f=${data};Plotly.newPlot('chart',f.data,f.layout,{responsive:true});</script></html>`,
        ],
        { type: "text/html" },
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "databuddy-chart.html";
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      setError("The chart could not be exported. Try again.");
    }
  }
  return (
    <section aria-label={description || "Analysis chart"}>
      <Plot
        data={figure.data}
        layout={layout}
        config={{ responsive: true, displaylogo: false, displayModeBar: false }}
        useResizeHandler
        style={{ width: "100%" }}
        onInitialized={(_, el) => {
          graph.current = el;
        }}
        onError={() =>
          setError(
            "The chart could not be displayed. Open Result data to inspect the values.",
          )
        }
      />
      <p className="chart-caption">
        {description ||
          "Chart from your data. Open Result data for the calculated values."}
      </p>
      <div className="actions">
        <button onClick={png}>Download PNG</button>
        <button onClick={html}>Download HTML</button>
      </div>
      {error ? (
        <p role="alert" className="error">
          {error}
        </p>
      ) : null}
    </section>
  );
}
