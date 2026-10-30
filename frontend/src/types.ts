export interface CallUsage {
  provider: string;
  model: string;
  input: number | null;
  output: number | null;
  total: number | null;
  reasoning: number | null;
  cached: number | null;
  at: string;
}
export interface ExchangeUsage {
  total: number;
  complete: boolean;
  calls: CallUsage[];
  attempts: number;
  fallbacks: number;
  limits: { provider: string; values: Record<string, string>; at: string }[];
}
export interface Usage extends ExchangeUsage {
  used: number;
  allowance: number;
  remaining: number;
  adjusted: boolean;
  last: ExchangeUsage | null;
  input_baseline: number;
  exchange_baseline: number;
}
export interface Dataset {
  filename: string;
  rows: number;
  columns: string[];
  preview: (string | number | boolean | null)[][];
  warnings: string[];
  numeric: string[];
  categories: string[];
  suggestion_columns?: SuggestionColumn[];
}
export interface SuggestionColumn {
  name: string;
  kind: "number" | "category" | "date" | "text";
  distinct: number | null;
  missing: number | null;
  identifier: boolean;
}
export interface Turn {
  id: string;
  question: string;
  answer: string;
  status: string;
  chart_json: string | null;
  chart_description: string | null;
  result_text: string | null;
  code: string | null;
  memory_notice: string | null;
  visualization_suggestion: string | null;
  result_table?: {
    columns: string[];
    rows: (string | number | null)[][];
    index: string[];
    total_rows: number;
    total_columns: number;
  } | null;
}
export interface Session {
  dataset: Dataset | null;
  turns: Turn[];
  usage: Usage;
  job: {
    id?: string;
    state: "running" | "done";
    stage: string;
    question?: string;
    answer_done?: boolean;
    stop_requested?: boolean;
  } | null;
}

export interface ResponseUpdate {
  id: string;
  version: number;
  job: NonNullable<Session["job"]>;
  answer: string;
  status: string;
  answer_done: boolean;
  notice: string;
  evidence?: Partial<Turn>;
}
