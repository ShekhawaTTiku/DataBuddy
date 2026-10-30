import {
  lazy,
  memo,
  Suspense,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import {
  ArrowUp,
  BarChart3,
  Check,
  ChevronRight,
  Copy,
  Database,
  FileSpreadsheet,
  Info,
  Menu,
  Moon,
  Paperclip,
  Plus,
  Square,
  SlidersHorizontal,
  Sparkles,
  Sun,
  Trash2,
  X,
} from "lucide-react";
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
  Message,
  MessageActions,
} from "./ChatPrimitives";
import { readPreferences, savePreferences } from "./preferences";
import {
  ApiError,
  readSession,
  request,
  startSession,
  watchResponse,
} from "./api";
import type { CallUsage, Session, Turn, Usage, ResponseUpdate } from "./types";
import Modal from "./Modal";
import ResultTable from "./ResultTable";
import TaskSuggestions from "./TaskSuggestions";
const Chart = lazy(() => import("./Chart"));
const AnswerText = lazy(() => import("./AnswerText"));
const ChartThumbnail = lazy(() =>
  import("./Chart").then((module) => ({ default: module.ChartThumbnail })),
);
const number = (value: number | null) =>
  value === null ? "Unavailable" : new Intl.NumberFormat().format(value);
type Panel = {
  type: "dataset" | "about" | "analysis" | "reset" | "remove" | "replace";
  turn?: Turn;
  file?: File;
  sample?: boolean;
};

function UsageCard({ usage }: { usage: Usage }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const keyboardFocus = useRef(false);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | undefined>(
    undefined,
  );
  const cancelClose = () => clearTimeout(closeTimer.current);
  const show = () => {
    cancelClose();
    setOpen(true);
  };
  useEffect(() => () => clearTimeout(closeTimer.current), []);
  useEffect(() => {
    if (!open) return;
    const close = (event: PointerEvent) => {
      if (!ref.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [open]);
  const groups: Record<string, CallUsage[]> = {};
  for (const call of usage.calls)
    (groups[`${call.provider} / ${call.model}`] ||= []).push(call);
  const limits = usage.limits?.at(-1);
  return (
    <div
      ref={ref}
      className="usage-wrap"
      onPointerDown={() => {
        keyboardFocus.current = false;
      }}
      onFocusCapture={(e) => {
        keyboardFocus.current = e.target.matches(":focus-visible");
      }}
      onMouseEnter={show}
      onMouseLeave={() => {
        cancelClose();
        closeTimer.current = setTimeout(() => {
          if (
            !keyboardFocus.current ||
            !ref.current?.contains(document.activeElement)
          )
            setOpen(false);
        }, 180);
      }}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) {
          setOpen(false);
        }
      }}
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          setOpen(false);
        }
      }}
    >
      <button
        className="icon-button"
        aria-label="Session usage"
        aria-expanded={open}
        aria-controls="usage-card"
        onFocus={show}
        onClick={show}
      >
        <SlidersHorizontal size={18} />
      </button>
      {open ? (
        <section
          className="usage-card"
          id="usage-card"
          aria-label="Session usage details"
        >
          <div className="row">
            <h2>Session usage</h2>
            <span className="muted">
              {usage.used} / {usage.allowance} messages
            </span>
          </div>
          <div className="usage-count">
            <strong>{usage.remaining}</strong>
            <span>messages remaining</span>
          </div>
          {usage.adjusted ? (
            <p className="warning">
              High usage reduced this session’s allowance by{" "}
              {15 - usage.allowance}{" "}
              {15 - usage.allowance === 1 ? "message" : "messages"}.
            </p>
          ) : null}
          <dl>
            <div>
              <dt>Reported tokens</dt>
              <dd>
                {usage.calls.some((c) => c.total !== null)
                  ? number(usage.total)
                  : "Unavailable"}
              </dd>
            </div>
            <div>
              <dt>Last exchange</dt>
              <dd>
                {usage.last?.calls.some((c) => c.total !== null)
                  ? number(usage.last.total)
                  : "Unavailable"}
              </dd>
            </div>
            <div>
              <dt>Observed attempts / fallbacks</dt>
              <dd>
                {usage.attempts} / {usage.fallbacks}
              </dd>
            </div>
          </dl>
          {Object.entries(groups).map(([name, calls]) => (
            <details key={name}>
              <summary>{name}</summary>
              <dl>
                <div>
                  <dt>Input / output</dt>
                  <dd>
                    {calls!.some((c) => c.input !== null)
                      ? number(calls!.reduce((v, c) => v + (c.input || 0), 0))
                      : "Unavailable"}{" "}
                    /{" "}
                    {calls!.some((c) => c.output !== null)
                      ? number(calls!.reduce((v, c) => v + (c.output || 0), 0))
                      : "Unavailable"}
                  </dd>
                </div>
                <div>
                  <dt>Reasoning / cached</dt>
                  <dd>
                    {calls!.some((c) => c.reasoning !== null)
                      ? number(
                          calls!.reduce((v, c) => v + (c.reasoning || 0), 0),
                        )
                      : "Unavailable"}{" "}
                    /{" "}
                    {calls!.some((c) => c.cached !== null)
                      ? number(calls!.reduce((v, c) => v + (c.cached || 0), 0))
                      : "Unavailable"}
                  </dd>
                </div>
                <div>
                  <dt>Last reported</dt>
                  <dd>{new Date(calls!.at(-1)!.at).toLocaleTimeString()}</dd>
                </div>
              </dl>
            </details>
          ))}
          <p className="muted small">
            {usage.complete
              ? "Provider-reported totals for observed calls."
              : "Some usage is unavailable. Totals may be incomplete."}
          </p>
          {limits ? (
            <details>
              <summary>Groq reported limits</summary>
              <dl>
                {Object.entries(limits.values).map(([key, value]) => (
                  <div key={key}>
                    <dt>
                      {{
                        "x-ratelimit-remaining-requests":
                          "Requests left (daily)",
                        "x-ratelimit-remaining-tokens": "Tokens left (minute)",
                        "x-ratelimit-reset-requests":
                          "Request window resets in",
                        "x-ratelimit-reset-tokens": "Token window resets in",
                        "retry-after": "Retry after (seconds)",
                      }[key] || key}
                    </dt>
                    <dd>{value}</dd>
                  </div>
                ))}
              </dl>
              <p>
                Reported at {new Date(limits.at).toLocaleTimeString()}. Shared
                account limits can change.
              </p>
            </details>
          ) : null}
          <details>
            <summary>Limits and estimates</summary>
            <p>
              {limits
                ? "Other provider quotas and reset times are unavailable."
                : "Provider quota remaining and reset times are unavailable."}{" "}
              Limits are shared across the owner’s free accounts.
            </p>
            <p>
              15 messages is an app allowance. Submitted messages, including
              failures, count. Clearing chat keeps the allowance. One review
              after 3 messages may reduce it by up to 2.
            </p>
            <p>
              Input warning: approximately {number(usage.input_baseline)}{" "}
              tokens. Exchange baseline: {number(usage.exchange_baseline)}{" "}
              tokens, an offline estimate.
            </p>
          </details>
        </section>
      ) : null}
    </div>
  );
}

const MemoUsageCard = memo(UsageCard);
export default function App() {
  const [preferences] = useState(readPreferences);
  const [session, setSession] = useState<Session | null>(null);
  const [error, setError] = useState("");
  const [expired, setExpired] = useState(false);
  const [connecting, setConnecting] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [sending, setSending] = useState(false);
  const [draft, setDraft] = useState("");
  const [dark, setDark] = useState(preferences.dark);
  const [sidebar, setSidebar] = useState(preferences.sidebar);
  const [mobileMenu, setMobileMenu] = useState(false);
  const [panel, setPanel] = useState<Panel | null>(null);
  const [tab, setTab] = useState(preferences.analysisTab);
  const [copied, setCopied] = useState("");
  const [notice, setNotice] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const composer = useRef<HTMLTextAreaElement>(null);
  const [pendingQuestion, setPendingQuestion] = useState("");
  const [response, setResponse] = useState<ResponseUpdate | null>(null);
  const focusRequested = useRef(true);
  const submission = useRef(false);
  const uncertain = useRef<{ id: string; question: string } | null>(null);
  const poll = session?.job?.state === "running";
  const busy = connecting || uploading || sending || poll || expired;
  const dataset = session?.dataset;
  const waitingForContent = !!pendingQuestion || poll;
  const jobId = session?.job?.id;
  const activeResponse = poll && response?.id === jobId ? response : null;
  const streamingTurn: Turn | null =
    activeResponse &&
    (activeResponse.answer ||
      activeResponse.evidence?.result_text ||
      activeResponse.evidence?.chart_json)
      ? {
          id: activeResponse.id,
          question: session?.job?.question || "",
          answer: activeResponse.answer,
          status: activeResponse.status,
          chart_json: null,
          chart_description: null,
          result_text: null,
          code: null,
          memory_notice: null,
          visualization_suggestion: null,
          ...activeResponse.evidence,
        }
      : null;
  const visibleTurns = streamingTurn
    ? [
        ...(session?.turns || []).filter((t) => t.id !== streamingTurn.id),
        streamingTurn,
      ]
    : session?.turns || [];
  const highInput =
    Math.ceil(draft.length / 4) > (session?.usage.input_baseline || 600);

  function failure(e: unknown) {
    setError(
      e instanceof Error ? e.message : "Something went wrong. Try again.",
    );
    if (e instanceof ApiError && e.status === 401) setExpired(true);
  }
  async function connect(fresh = false) {
    setConnecting(true);
    setError("");
    try {
      setSession(await startSession(fresh));
      setExpired(false);
      focusRequested.current = true;
    } catch (e) {
      failure(e);
    } finally {
      setConnecting(false);
    }
  }
  useEffect(() => {
    void connect();
  }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute("content", dark ? "#19211E" : "#F7F6F2");
  }, [dark]);
  useEffect(() => {
    savePreferences({ dark, sidebar, analysisTab: tab });
  }, [dark, sidebar, tab]);
  useEffect(() => {
    if (busy || panel || mobileMenu || !focusRequested.current) return;
    const frame = requestAnimationFrame(() => {
      composer.current?.focus({ preventScroll: true });
      focusRequested.current = false;
    });
    return () => cancelAnimationFrame(frame);
  }, [busy, panel, mobileMenu]);
  useEffect(() => {
    if (!poll || expired || !jobId) return;
    let cancelled = false;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function update() {
      try {
        await watchResponse(
          jobId!,
          (next) => {
            if (cancelled) return;
            setResponse((previous) => ({
              ...next,
              evidence:
                next.evidence ??
                (previous?.id === next.id ? previous.evidence : {}),
            }));
            setSession((current) =>
              current?.job?.id === next.id
                ? { ...current, job: { ...next.job, state: "running" } }
                : current,
            );
          },
          controller.signal,
        );
        if (!cancelled) setSession(await readSession());
        if (!cancelled) setError("");
      } catch (e) {
        if (!cancelled) {
          try {
            const progress = await request<Pick<Session, "job">>("/job");
            if (cancelled) return;
            if (progress.job?.state !== "running") {
              setSession(await readSession());
              setError("");
              return;
            }
            setError("Response connection interrupted. Reconnecting…");
          } catch (recoveryError) {
            if (!cancelled) failure(recoveryError);
          }
          if (!cancelled) timer = setTimeout(update, 2500);
        }
      }
    }
    void update();
    return () => {
      cancelled = true;
      controller.abort();
      clearTimeout(timer);
    };
  }, [poll, expired, jobId]);
  useEffect(() => {
    if (!draft && !poll) return;
    const warn = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [draft, poll]);

  async function load(file?: File, sample = false) {
    if (file && file.size > 20 * 1024 * 1024) {
      setError("Choose a file smaller than 20 MiB.");
      return;
    }
    if (file && !/\.(csv|xlsx)$/i.test(file.name)) {
      setError("Choose a CSV or XLSX file.");
      return;
    }
    setUploading(true);
    setError("");
    setPanel(null);
    try {
      const next = sample
        ? await request<Session>("/sample", { method: "POST" })
        : await request<Session>("/dataset", {
            method: "PUT",
            headers: {
              "Content-Type": "application/octet-stream",
              "X-Filename": encodeURIComponent(file!.name),
            },
            body: file,
          });
      setSession(next);
      setNotice("Dataset ready.");
      setMobileMenu(false);
      focusRequested.current = true;
    } catch (e) {
      failure(e);
    } finally {
      setUploading(false);
      if (input.current) input.current.value = "";
    }
  }
  function choose(file?: File, sample = false) {
    if (dataset) setPanel({ type: "replace", file, sample });
    else void load(file, sample);
  }
  async function mutate(path: string, method = "POST") {
    setPanel(null);
    setSending(true);
    setError("");
    try {
      setSession(await request<Session>(path, { method }));
      focusRequested.current = true;
      setNotice(
        path === "/reset"
          ? "Chat cleared. Message allowance kept."
          : "Dataset removed. Message allowance kept.",
      );
    } catch (e) {
      failure(e);
    } finally {
      setSending(false);
    }
  }
  async function send(e: FormEvent) {
    e.preventDefault();
    if (busy || submission.current) return;
    if (!dataset) {
      setError("Upload data or try the sample first.");
      composer.current?.focus();
      return;
    }
    if (!draft.trim()) {
      setError("Enter a question first.");
      composer.current?.focus();
      return;
    }
    submission.current = true;
    setSending(true);
    setError("");
    setNotice("");
    const question = draft.trim();
    setPendingQuestion(question);
    const id =
      uncertain.current?.question === question
        ? uncertain.current.id
        : crypto.randomUUID();
    uncertain.current = { id, question };
    try {
      await request("/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, request_id: id }),
      });
      // Start polling even if the next snapshot fails; accepted work is not resubmitted.
      setSession((s) =>
        s
          ? {
              ...s,
              job: {
                id,
                state: "running",
                stage: "Understanding question",
                question,
              },
            }
          : s,
      );
      setDraft("");
      uncertain.current = null;
    } catch (e) {
      try {
        const next = await readSession();
        setSession(next);
        if (next.job?.id === id || next.turns.some((t) => t.id === id)) {
          setDraft("");
          uncertain.current = null;
        } else failure(e);
      } catch {
        failure(e);
      }
      if (e instanceof ApiError && e.status >= 400) uncertain.current = null;
    } finally {
      submission.current = false;
      setSending(false);
      setPendingQuestion("");
    }
  }
  async function stopResponse() {
    if (!jobId) return;
    try {
      const result = await request<{ stopping: boolean }>(
        `/jobs/${jobId}/cancel`,
        { method: "POST" },
      );
      if (result.stopping)
        setSession((current) =>
          current?.job?.id === jobId
            ? {
                ...current,
                job: {
                  ...current.job,
                  stop_requested: true,
                  stage: "Stopping response",
                },
              }
            : current,
        );
    } catch (e) {
      failure(e);
    }
  }
  function analyze(turn: Turn, view: string) {
    setTab(view);
    setPanel({ type: "analysis", turn });
  }
  async function copy(turn: Turn) {
    try {
      await navigator.clipboard.writeText(turn.answer);
      setCopied(turn.id);
      setNotice("Answer copied.");
      setTimeout(() => setCopied(""), 2000);
    } catch {
      setNotice("Copy is unavailable. Select the answer text to copy it.");
    }
  }
  function prompt(value: string) {
    setDraft(value);
    composer.current?.focus();
    if (!dataset)
      setNotice("Upload data or try the sample to ask this question.");
  }

  const sideContent = (
    <>
      <a
        href="#main"
        className="brand"
        aria-label="DataBuddy home"
        translate="no"
        onClick={() => setMobileMenu(false)}
      >
        <span className="brand-mark">
          <BarChart3 size={21} />
        </span>
        DataBuddy
      </a>
      <button
        className="new-chat"
        disabled={busy || !session?.turns.length}
        onClick={() => {
          setMobileMenu(false);
          setPanel({ type: "reset" });
        }}
      >
        <Plus size={18} />
        Clear chat
      </button>
      <div className="sidebar-dataset">
        <h2>Dataset</h2>
        {dataset ? (
          <>
            <button
              className="dataset-button"
              onClick={() => {
                setMobileMenu(false);
                setPanel({ type: "dataset" });
              }}
            >
              <FileSpreadsheet size={20} />
              <span>
                <strong>{dataset.filename}</strong>
                <small>
                  {number(dataset.rows)} rows · {dataset.columns.length} columns
                </small>
              </span>
              <ChevronRight size={16} />
            </button>
            <button
              className="text-button"
              disabled={busy}
              onClick={() => {
                setMobileMenu(false);
                setPanel({ type: "remove" });
              }}
            >
              <Trash2 size={14} />
              Remove dataset
            </button>
          </>
        ) : (
          <p className="muted small">No dataset loaded</p>
        )}
      </div>
      {session?.turns.length ? (
        <nav className="session-list" aria-label="This session">
          <h2>This session</h2>
          {session.turns.map((t) => (
            <a
              key={t.id}
              href={`#turn-${t.id}`}
              onClick={() => {
                setMobileMenu(false);
                focusRequested.current = true;
                requestAnimationFrame(() =>
                  composer.current?.focus({ preventScroll: true }),
                );
              }}
            >
              {t.question}
            </a>
          ))}
        </nav>
      ) : null}
      <footer className="sidebar-footer">
        <div className="row">
          <button
            className="text-button"
            onClick={() => {
              setMobileMenu(false);
              setPanel({ type: "about" });
            }}
          >
            <Info size={16} />
            About
          </button>
          <button
            className="icon-button"
            aria-label={dark ? "Use light theme" : "Use dark theme"}
            onClick={() => setDark(!dark)}
          >
            {dark ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </div>
        <span className="small muted">Session only</span>
      </footer>
    </>
  );

  return (
    <div className={`app ${sidebar ? "" : "sidebar-hidden"}`}>
      <a className="skip-link" href="#main">
        Skip to chat
      </a>
      {sidebar ? <aside className="sidebar">{sideContent}</aside> : null}
      <main id="main" tabIndex={-1}>
        <header className="topbar">
          <div className="row">
            <button
              className="icon-button desktop-menu"
              aria-label={sidebar ? "Hide sidebar" : "Show sidebar"}
              onClick={() => setSidebar(!sidebar)}
            >
              <Menu size={20} />
            </button>
            <button
              className="icon-button mobile-menu"
              aria-label="Open sidebar"
              onClick={() => setMobileMenu(true)}
            >
              <Menu size={20} />
            </button>
            <span className="topbar-name">DataBuddy</span>
          </div>
          <div className="row">
            {dataset ? (
              <button
                className="top-dataset"
                aria-label={`Preview dataset: ${dataset.filename}`}
                onClick={() => setPanel({ type: "dataset" })}
              >
                <Database size={16} />
                <span>{dataset.filename}</span>
              </button>
            ) : null}
            {session ? <MemoUsageCard usage={session.usage} /> : null}
          </div>
        </header>
        <div
          className={`workspace ${session?.turns.length || poll ? "has-chat" : ""}`}
        >
          <Conversation
            className="conversation-region"
            aria-label="Conversation history"
          >
            <ConversationContent
              scrollClassName="conversation-scroll"
              className="conversation-content"
            >
              <div className="conversation">
                {!session?.turns.length && !waitingForContent ? (
                  <section className="welcome">
                    <span className="welcome-mark">
                      <BarChart3 size={30} strokeWidth={1.6} />
                    </span>
                    <h1>
                      {dataset ? "Ask about your data" : "Start with your data"}
                    </h1>
                    <p>
                      {dataset
                        ? `${number(dataset.rows)} rows ready to explore.`
                        : "Upload a spreadsheet, then ask a question."}
                    </p>
                    {!dataset ? (
                      <>
                        <div className="welcome-actions">
                          <button
                            className="primary"
                            disabled={busy || !session}
                            onClick={() => input.current?.click()}
                          >
                            <Plus size={18} />
                            Upload data
                          </button>
                          <button
                            disabled={busy || !session}
                            onClick={() => choose(undefined, true)}
                          >
                            Try sample data
                          </button>
                        </div>
                        <span className="small muted">
                          CSV or XLSX · Up to 20 MiB
                        </span>
                      </>
                    ) : (
                      <button
                        className="text-button"
                        onClick={() => setPanel({ type: "dataset" })}
                      >
                        <FileSpreadsheet size={16} />
                        Preview dataset
                        <ChevronRight size={14} />
                      </button>
                    )}
                  </section>
                ) : (
                  <>
                    <h1 className="sr-only">Data analysis conversation</h1>
                    {visibleTurns.map((turn) => (
                      <article
                        className="exchange"
                        id={`turn-${turn.id}`}
                        key={turn.id}
                      >
                        <Message from="user" className="question">
                          <span className="sr-only">You: </span>
                          {turn.question}
                        </Message>
                        <Message from="assistant" className="answer">
                          <div className="answer-label">
                            <span className="mini-mark">
                              <BarChart3 size={14} />
                            </span>
                            DataBuddy
                            {turn.status === "partial" ? (
                              <span className="status-tag">Partial result</span>
                            ) : null}
                            {turn.status === "stopped" ? (
                              <span className="status-tag">Stopped</span>
                            ) : null}
                          </div>
                          {turn.answer ? (
                            <Suspense
                              fallback={
                                <div className="prose answer-fallback">
                                  {turn.answer}
                                </div>
                              }
                            >
                              <AnswerText
                                answer={turn.answer}
                                failed={turn.status === "error"}
                                dark={dark}
                                streaming={
                                  turn.id === activeResponse?.id &&
                                  !activeResponse.answer_done
                                }
                              />
                            </Suspense>
                          ) : (
                            <p className="small muted">
                              Your result is ready. Preparing the explanation…
                            </p>
                          )}
                          {turn.chart_json ? (
                            <div className="chart-card">
                              <Suspense
                                fallback={
                                  <p className="small muted">
                                    Loading chart preview…
                                  </p>
                                }
                              >
                                <ChartThumbnail
                                  json={turn.chart_json}
                                  dark={dark}
                                />
                              </Suspense>
                              <button
                                className="chart-preview"
                                onClick={() => analyze(turn, "Chart")}
                              >
                                <BarChart3 size={30} />
                                <span>
                                  <strong>
                                    {turn.chart_description || "Chart ready"}
                                  </strong>
                                  <small>Open interactive chart</small>
                                </span>
                                <ChevronRight size={20} />
                              </button>
                            </div>
                          ) : null}
                          <MessageActions>
                            {turn.result_text ? (
                              <button
                                onClick={() => analyze(turn, "Result data")}
                              >
                                Result data
                              </button>
                            ) : null}
                            {turn.code ? (
                              <button
                                onClick={() => analyze(turn, "Calculation")}
                              >
                                Calculation
                              </button>
                            ) : null}
                            <button
                              className="icon-button"
                              aria-label="Copy answer"
                              onClick={() => copy(turn)}
                            >
                              {copied === turn.id ? (
                                <Check size={16} />
                              ) : (
                                <Copy size={16} />
                              )}
                            </button>
                          </MessageActions>
                          {turn.memory_notice ? (
                            <details className="memory-note">
                              <summary>Memory notice</summary>
                              <p>{turn.memory_notice}</p>
                            </details>
                          ) : null}
                        </Message>
                      </article>
                    ))}
                    {waitingForContent ? (
                      <div className="exchange">
                        {!streamingTurn ? (
                          <Message from="user" className="question">
                            {session?.job?.state === "running"
                              ? session.job.question
                              : pendingQuestion}
                          </Message>
                        ) : null}
                        {activeResponse?.notice &&
                        !activeResponse.answer_done ? (
                          <p className="small muted" role="status">
                            {activeResponse.notice}
                          </p>
                        ) : null}
                        <p className="progress" role="status">
                          <span className="progress-dot" />
                          {poll
                            ? session?.job?.stage || "Preparing answer"
                            : "Sending question"}
                          …
                        </p>
                      </div>
                    ) : null}
                  </>
                )}
              </div>
            </ConversationContent>
            <ConversationScrollButton />
          </Conversation>
          <div className="composer-area">
            <TaskSuggestions
              dataset={dataset}
              disabled={busy || !session || session.usage.remaining === 0}
              onChoose={prompt}
              hasResult={
                !!session?.turns.some(
                  (turn) => turn.result_text || turn.chart_json,
                )
              }
            />
            {error ? (
              <div className="error-banner" role="alert">
                <span>{error}</span>
                {expired ? (
                  <button onClick={() => connect(true)}>
                    Start new session
                  </button>
                ) : !session ? (
                  <button disabled={connecting} onClick={() => connect()}>
                    Retry connection
                  </button>
                ) : (
                  <button
                    className="icon-button"
                    aria-label="Dismiss error"
                    onClick={() => setError("")}
                  >
                    <X size={16} />
                  </button>
                )}
              </div>
            ) : null}
            {session?.usage.adjusted ? (
              <p className="warning small" role="status">
                High usage: allowance adjusted to {session.usage.allowance}{" "}
                messages.
              </p>
            ) : null}
            {session && session.usage.remaining === 0 && !poll ? (
              <p className="allowance-notice" role="status">
                Session allowance reached. You can still review your answers and
                download charts.
              </p>
            ) : null}
            <form className="composer" onSubmit={send}>
              <label htmlFor="question" className="sr-only">
                Question about your data
              </label>
              <textarea
                id="question"
                name="question"
                autoComplete="off"
                ref={composer}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                maxLength={4000}
                rows={2}
                placeholder={
                  dataset
                    ? "Ask a question about your data…"
                    : "What would you like to explore…"
                }
                aria-describedby={highInput ? "input-warning" : undefined}
                onKeyDown={(e) => {
                  if (
                    e.key === "Enter" &&
                    !e.shiftKey &&
                    !e.nativeEvent.isComposing
                  ) {
                    e.preventDefault();
                    e.currentTarget.form?.requestSubmit();
                  }
                }}
              />
              <div className="composer-tools">
                <div className="row">
                  <button
                    type="button"
                    className="icon-button"
                    disabled={busy || !session}
                    aria-label="Attach dataset"
                    onClick={() => input.current?.click()}
                  >
                    <Paperclip size={19} />
                  </button>
                  {dataset ? (
                    <span className="composer-file">{dataset.filename}</span>
                  ) : null}
                </div>
                {poll && !session?.job?.answer_done ? (
                  <button
                    className="send"
                    type="button"
                    aria-label="Stop response"
                    disabled={session?.job?.stop_requested}
                    onClick={() => void stopResponse()}
                  >
                    <Square size={18} fill="currentColor" />
                  </button>
                ) : (
                  <button
                    className="send"
                    type="submit"
                    aria-label="Send message"
                    disabled={busy || !session || session.usage.remaining === 0}
                  >
                    <ArrowUp size={21} />
                  </button>
                )}
              </div>
            </form>
            {highInput ? (
              <div className="input-warning" id="input-warning" role="status">
                <span>
                  ≈ {number(Math.ceil(draft.length / 4))} input tokens
                </span>
                <details
                  onMouseEnter={(e) => {
                    e.currentTarget.open = true;
                  }}
                  onMouseLeave={(e) => {
                    if (!e.currentTarget.contains(document.activeElement))
                      e.currentTarget.open = false;
                  }}
                >
                  <summary aria-label="About high token usage">
                    <Info size={15} />
                  </summary>
                  <p>
                    This is a rough text estimate. Consistently high usage may
                    reduce your session allowance by 1–2 messages.
                    Provider-reported usage appears in Session usage.
                  </p>
                </details>
              </div>
            ) : null}
            <div className="composer-foot">
              <span role="status">
                {connecting
                  ? "Connecting to server…"
                  : uploading
                    ? "Reading dataset…"
                    : notice}
              </span>
            </div>
          </div>
        </div>
        <input
          className="sr-only"
          tabIndex={-1}
          ref={input}
          name="dataset"
          type="file"
          aria-label="Choose dataset"
          accept=".csv,.xlsx"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) choose(file);
            e.target.value = "";
          }}
        />
      </main>
      {mobileMenu ? (
        <Modal title="DataBuddy" close={() => setMobileMenu(false)}>
          <nav className="mobile-sidebar">{sideContent}</nav>
        </Modal>
      ) : null}
      {panel ? (
        <Modal
          title={
            panel.type === "dataset"
              ? "Dataset preview"
              : panel.type === "analysis"
                ? "Analysis"
                : panel.type === "about"
                  ? "About DataBuddy"
                  : panel.type === "reset"
                    ? "Clear this chat?"
                    : panel.type === "remove"
                      ? "Remove this dataset?"
                      : "Replace this dataset?"
          }
          close={() => setPanel(null)}
          panel={panel.type === "analysis" || panel.type === "dataset"}
          wide={panel.type === "analysis" && tab === "Chart"}
        >
          {panel.type === "dataset" && dataset ? (
            <>
              <p className="muted">
                {dataset.filename} · {number(dataset.rows)} rows ·{" "}
                {dataset.columns.length} columns
              </p>
              <div
                className="table-scroll"
                tabIndex={0}
                role="region"
                aria-label="Dataset sample"
              >
                <table>
                  <caption>First {Math.min(12, dataset.rows)} rows</caption>
                  <thead>
                    <tr>
                      {dataset.columns.map((c) => (
                        <th key={c} scope="col">
                          {c}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {dataset.preview.map((row, i) => (
                      <tr key={i}>
                        {row.map((cell, j) => (
                          <td key={j}>
                            {cell === null ? (
                              <span className="muted">Missing</span>
                            ) : (
                              String(cell)
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {dataset.warnings.length ? (
                <details>
                  <summary>Import notes ({dataset.warnings.length})</summary>
                  {dataset.warnings.map((w) => (
                    <p key={w}>{w}</p>
                  ))}
                </details>
              ) : null}
              <p className="small muted">XLSX imports use the first sheet.</p>
            </>
          ) : null}
          {panel.type === "analysis" && panel.turn ? (
            <>
              <div className="tabs" role="group" aria-label="Analysis views">
                {["Chart", "Result data", "Calculation"]
                  .filter((t) => t !== "Chart" || panel.turn!.chart_json)
                  .map((t) => (
                    <button
                      key={t}
                      aria-pressed={tab === t}
                      onClick={() => setTab(t)}
                    >
                      {t}
                    </button>
                  ))}
              </div>
              {tab === "Chart" && panel.turn.chart_json ? (
                <Suspense fallback={<p role="status">Loading chart…</p>}>
                  <Chart
                    json={panel.turn.chart_json}
                    description={panel.turn.chart_description || ""}
                    dark={dark}
                  />
                </Suspense>
              ) : tab === "Result data" && panel.turn.result_table ? (
                <ResultTable table={panel.turn.result_table} />
              ) : (
                <pre tabIndex={0} className="result-code">
                  {tab === "Calculation"
                    ? panel.turn.code
                    : panel.turn.result_text || "No result data was returned."}
                </pre>
              )}
            </>
          ) : null}
          {panel.type === "about" ? (
            <div className="about">
              <p>
                Ask questions about a spreadsheet and inspect the calculations
                behind each answer.
              </p>
              <h3>Your data</h3>
              <p>
                Data and chat stay in temporary server memory. Inactive sessions
                expire after 30 minutes; server restarts also clear them.
                Relevant dataset samples, summaries and questions are sent to
                Groq, Google Gemini and Mistral.
              </p>
              <p>
                Use non-sensitive demo data. Basic execution checks are not a
                hardened security sandbox.
              </p>
              <h3>Message allowance</h3>
              <p>
                Each session starts with 15 messages. High usage may reduce this
                to 13 or 14. Free provider limits can be reached earlier.
                Clearing chat or replacing a dataset keeps the allowance.
              </p>
              <p>Check computed results before relying on an answer.</p>
            </div>
          ) : null}
          {["reset", "remove", "replace"].includes(panel.type) ? (
            <>
              <p>
                {panel.type === "reset"
                  ? "This clears the conversation and its memory."
                  : "This clears the current dataset, conversation and memory."}{" "}
                Your message allowance stays the same.
              </p>
              <div className="modal-actions">
                <button onClick={() => setPanel(null)}>Cancel</button>
                <button
                  className="primary"
                  onClick={() =>
                    panel.type === "replace"
                      ? load(panel.file, panel.sample)
                      : mutate(
                          panel.type === "reset" ? "/reset" : "/dataset",
                          panel.type === "remove" ? "DELETE" : "POST",
                        )
                  }
                >
                  {panel.type === "reset"
                    ? "Clear chat"
                    : panel.type === "remove"
                      ? "Remove dataset"
                      : "Replace dataset"}
                </button>
              </div>
            </>
          ) : null}
        </Modal>
      ) : null}
    </div>
  );
}
