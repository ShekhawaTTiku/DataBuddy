import { memo, useRef, useState } from "react";
import createPlotlyComponent from "react-plotly.js/factory";
import Plotly from "plotly.js-dist-min";
import { chartGeometry, readableLayout, type Figure } from "./chartLayout";
const Plot = createPlotlyComponent(Plotly);

export const ChartThumbnail = memo(function ChartThumbnail({
  json,
  dark,
}: {
  json: string;
  dark: boolean;
}) {
  const figure = JSON.parse(json) as Figure;
  const geometry = chartGeometry(figure);
  return (
    <div
      className="chart-scroll chart-thumbnail"
      tabIndex={geometry.dashboard ? 0 : undefined}
      role="region"
      aria-label="Chart preview"
    >
      <div style={{ minWidth: geometry.width || undefined }}>
        <Plot
          data={figure.data}
          layout={readableLayout(figure, dark, true)}
          config={{ staticPlot: true, responsive: true, displayModeBar: false }}
          useResizeHandler
          style={{
            width: "100%",
            height: readableLayout(figure, dark, true).height,
          }}
        />
      </div>
      {geometry.dashboard ? (
        <p className="chart-scroll-hint">
          {geometry.panels} panels · Scroll sideways for the full preview
        </p>
      ) : null}
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
  const figure = JSON.parse(json) as Figure;
  const geometry = chartGeometry(figure);
  const layout = readableLayout(figure, dark);
  async function png() {
    try {
      if (graph.current)
        await Plotly.downloadImage(graph.current, {
          format: "png",
          filename: "databuddy-chart",
          width: Math.max(1200, geometry.width),
          height: geometry.height,
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
        layout: { ...layout, autosize: true, width: undefined },
      }).replace(/</g, "\\u003c");
      const blob = new Blob(
        [
          `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DataBuddy chart</title><style>body{margin:0;overflow-x:auto;background:${dark ? "#222A27" : "#FFFFFF"}}#chart{min-width:${geometry.width || 350}px;height:${geometry.height}px}</style><div id="chart"></div><script>${source.replace(/<\/script/gi, "<\\/script")}</script><script>const f=${data};Plotly.newPlot('chart',f.data,f.layout,{responsive:true});</script></html>`,
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
      {geometry.dashboard ? (
        <p className="small muted">
          Scroll sideways on smaller screens to view every panel.
        </p>
      ) : null}
      <div
        className="chart-scroll"
        tabIndex={0}
        role="region"
        aria-label="Interactive chart"
      >
        <div style={{ minWidth: geometry.width || undefined }}>
          <Plot
            data={figure.data}
            layout={layout}
            config={{
              responsive: true,
              displaylogo: false,
              displayModeBar: false,
            }}
            useResizeHandler
            style={{ width: "100%", height: layout.height }}
            onInitialized={(_, el) => {
              graph.current = el;
            }}
            onError={() =>
              setError(
                "The chart could not be displayed. Open Result data to inspect the values.",
              )
            }
          />
        </div>
      </div>
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
