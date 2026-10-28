import { memo } from "react";
import { Streamdown, defaultRehypePlugins } from "streamdown";
import { math } from "@streamdown/math";
import { createMermaidPlugin } from "@streamdown/mermaid";
import "streamdown/styles.css";
import "./streamdown.css";
import "katex/dist/katex.min.css";

const plugins = {
  math,
  mermaid: createMermaidPlugin({
    config: { securityLevel: "strict", startOnLoad: false },
  }),
};
// Keep raw HTML disabled and don't fetch images embedded in generated text.
const rehypePlugins = [
  defaultRehypePlugins.sanitize,
  defaultRehypePlugins.harden,
];
const components = { img: () => null };
const diagramOptions = {
  light: { config: { theme: "default", securityLevel: "strict" } },
  dark: { config: { theme: "dark", securityLevel: "strict" } },
} as const;

export default memo(function AnswerText({
  answer,
  failed,
  streaming = false,
  dark = false,
}: {
  answer: string;
  failed: boolean;
  streaming?: boolean;
  dark?: boolean;
}) {
  return (
    <div className={`prose ${failed ? "error-answer" : ""}`}>
      <Streamdown
        mode="streaming"
        isAnimating={streaming}
        plugins={plugins}
        mermaid={diagramOptions[dark ? "dark" : "light"]}
        rehypePlugins={rehypePlugins}
        components={components}
        controls={{
          code: { copy: true, download: true },
          table: { copy: true, download: true, fullscreen: false },
          mermaid: {
            copy: true,
            download: true,
            fullscreen: false,
            panZoom: true,
          },
        }}
        tableMaxHeight={0}
        codeBlockMaxHeight={0}
      >
        {answer ||
          "No response text was returned. Inspect any available results below."}
      </Streamdown>
    </div>
  );
});
