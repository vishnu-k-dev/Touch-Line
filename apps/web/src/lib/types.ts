export type TeamRef = { id: number; name: string };

export type Match = {
  id: number;
  date: string;
  stage: string;
  competition_id: number;
  season_id: number;
  home_team: TeamRef;
  away_team: TeamRef;
  home_score: number;
  away_score: number;
};

export type TeamStats = {
  team_id: number;
  team: string;
  goals: number;
  shots: number;
  shots_on_target: number;
  xg: number;
  np_xg: number;
  xg_per_shot: number;
  passes: number;
  passes_completed: number;
  pass_accuracy_pct: number;
  pass_share_pct: number;
  pressures: number;
  fouls_committed: number;
  corners: number;
  ppda: number | null;
  ppda_passes_allowed: number;
  ppda_defensive_actions: number;
  shootout_goals: number | null;
};

export type MatchStats = {
  match_id: number;
  home: TeamStats;
  away: TeamStats;
  definitions: Record<string, string>;
};

export type Shot = {
  event_id: string;
  team_id: number;
  team: string;
  player_id: number;
  player: string;
  display_name: string;
  period: number;
  minute: number;
  second: number;
  x: number | null;
  y: number | null;
  xg: number | null;
  outcome: string;
  shot_type: string | null;
  body_part: string | null;
  is_shootout: boolean;
  defenders_in_cone: number | null;
  cone_visible: boolean | null;
  nearest_defender: number | null;
};

export type PlayerStats = {
  player_id: number;
  player: string;
  display_name: string;
  team: string | null;
  shots: number;
  goals: number;
  xg: number;
  np_xg: number;
  passes: number;
  passes_completed: number;
  key_passes: number;
  assists: number;
  pressures: number;
  tackles: number;
  interceptions: number;
  minutes: number;
  started: boolean;
};

export type Heatmap = {
  match_id: number;
  team_id: number | null;
  player_id: number | null;
  kind: string;
  cols: number;
  rows: number;
  cell_yards: number;
  total: number;
  max: number;
  cells: number[][];
};

export type Finding = {
  claim: string;
  metric: string;
  values: Record<string, number | string>;
  sources: string[];
  evidence: string[];
  verified: boolean;
  problems: string[];
};

export type TraceStep = {
  step: number;
  tool: string;
  call_id: string;
  args: Record<string, unknown>;
  ok: boolean;
  ms: number;
  summary: string;
};

export type AnalystResult = {
  status: "answered" | "unverified" | "incomplete" | "refused";
  answer: { question: string; findings: Finding[]; interpretation: string; limitations: string[] } | null;
  message: string | null;
  validation: { passed: boolean; violations: string[] };
  trace: TraceStep[];
  usage: {
    model: string;
    steps: number;
    tool_calls: number;
    input_tokens: number;
    output_tokens: number;
    cache_read_tokens: number;
    cost_usd: number | null;
    latency_ms: number;
  };
};

export type AnalystStatus = { configured: boolean; provider: string; model: string };

export type HistoryTurn = { id: number; match_id: number | null; question: string; created_at: string; result: AnalystResult };
