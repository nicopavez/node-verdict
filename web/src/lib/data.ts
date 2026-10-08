// Typed access to the exported JSON. The web app renders; Python decides.
import raw from "@/data/node-verdict-data.json";

export type Reason = "NodeLemon" | "NodeSuspect" | "SDCSuspect" | "WorkloadImbalance";

export interface Evidence {
  signal: string;
  value: string;
  note?: string;
}

export interface Verdict {
  apiVersion: string;
  node: string;
  job: string;
  condition: {
    type: string;
    status: string;
    reason: Reason;
    message: string;
    lastTransitionTime: string;
    attributedTo: "node" | "job";
    confidence: "low" | "medium" | "high";
    evidence: Evidence[];
  };
  action: { kind: string; status: string; detail: string; changesNode: boolean };
}

export interface Rank {
  rank: number;
  node: string;
  stage: number;
  dp: number;
  meanComputeS: number;
  vsJobMedian: number;
  peerRatio: number;
  persistence: number;
  computeS: number[];
}

export interface Job {
  id: string;
  trace: string;
  traceLabel: string;
  cause: "node" | "workload";
  nodes: string[];
  steps: number[];
  stages: number[];
  dps: number[];
  stageRatio: Record<string, number>;
  fbCorr: number;
  stepCv: number;
  jobMedianComputeS: number;
  slowdown: number;
  fullJob: { dp_size: number; pp_size: number; tp_size: number; world_size: number };
  ranks: Rank[];
}

export interface Observation {
  job: string;
  current: boolean;
  persistentOutlier: boolean;
  peerRatio: number | null;
  anomalyEvents: number;
  excludedByJob: boolean;
  repairTickets: number;
  multiNodeFailure: boolean;
  activeCheckPassed: boolean | null;
}

export interface NodeHistory {
  elevatedJobs: number;
  anomalyJobs: number;
  lemonScore: number;
  activeCheckPassRate: number | null;
  observations: Observation[];
}

export interface Policy {
  name: string;
  replaced: string[];
  quarantined: string[];
  healthyReplaced: string[];
  sparesUsed: number;
  flaggedUnserved: number;
  badNodeFixed: boolean;
  sdcPulled: boolean;
  ownerByJob: Record<string, string>;
  jobsRightOwner: string[];
  goodput: number;
  goodputByJob: Record<string, number>;
}

export interface Band {
  param: string;
  default: number;
  low: number;
  high: number;
  grid_min: number;
  grid_max: number;
  below: string;
  above: string;
  basis: string;
}

export interface Data {
  meta: {
    version: string;
    apiVersion: string;
    asOf: string;
    poolSize: number;
    spares: number;
    real: string[];
    synthetic: string[];
    planted: { badNode: string; sdcNode: string; decoyNode: string };
  };
  config: Record<string, number | Record<string, number>>;
  simParams: Record<string, number>;
  reasonCodes: { code: Reason; attributedTo: string; defaultAction: string; when: string }[];
  pool: string[];
  jobs: Job[];
  verdicts: { withHistory: Verdict[]; noHistory: Verdict[] };
  ownerByJob: { withHistory: Partial<Record<string, "node" | "job">>; noHistory: Partial<Record<string, "node" | "job">> };
  history: Record<string, NodeHistory>;
  policies: Policy[];
  sensitivity: { ckptSteps: number; vsNaive: number; vsNaiveCheckpoint: number; vsPeerAware: number }[];
  robustness: { bands: Band[]; healthyNodesEverChanged: number };
}

export const data = raw as unknown as Data;

export const REASON_LABEL: Record<Reason, string> = {
  NodeLemon: "Bad node",
  SDCSuspect: "Corrupting chip",
  NodeSuspect: "Suspect node",
  WorkloadImbalance: "Job setup",
};

export const REASON_SHORT: Record<Reason, string> = {
  NodeLemon: "Lemon",
  SDCSuspect: "SDC",
  NodeSuspect: "Suspect",
  WorkloadImbalance: "Job",
};

export const REASON_VAR: Record<Reason, string> = {
  NodeLemon: "var(--v-lemon)",
  SDCSuspect: "var(--v-sdc)",
  NodeSuspect: "var(--v-suspect)",
  WorkloadImbalance: "var(--v-job)",
};

export const ACTION_LABEL: Record<string, string> = {
  ReplaceAtCheckpoint: "Replace at next checkpoint",
  QuarantineForRetest: "Quarantine and retest",
  Watch: "Watch, no change",
  InformCustomer: "Tell the customer",
};

export const POLICY_LABEL: Record<string, { title: string; blurb: string }> = {
  naive: { title: "Naive", blurb: "Replace any rank slower than the job median, mid-run." },
  "naive+checkpoint": { title: "Naive + checkpoint", blurb: "Same flags, but wait for a checkpoint." },
  "peer-aware": { title: "Peer-aware", blurb: "Replace a rank slow against its stage peers. The fair baseline." },
  attributed: { title: "Node Verdict", blurb: "Verdict engine plus policy." },
};

export function rankOfNode(node: string): { job: Job; rank: Rank } | null {
  for (const job of data.jobs) {
    const rank = job.ranks.find((r) => r.node === node);
    if (rank) return { job, rank };
  }
  return null;
}

export function verdictMap(withHistory: boolean): Map<string, Verdict> {
  const list = withHistory ? data.verdicts.withHistory : data.verdicts.noHistory;
  return new Map(list.map((v) => [v.node, v]));
}

/** Median of stage peers (the other replicas of the same stage), per step. */
export function peerMedianSeries(job: Job, rank: Rank): number[] {
  const peers = job.ranks.filter((r) => r.stage === rank.stage);
  return job.steps.map((_, i) => {
    const xs = peers.map((p) => p.computeS[i]).sort((a, b) => a - b);
    const m = xs.length / 2;
    return xs.length % 2 ? xs[Math.floor(m)] : (xs[m - 1] + xs[m]) / 2;
  });
}

export function heatLevel(x: number): number {
  if (x < 1.05) return 0;
  if (x < 1.15) return 1;
  if (x < 1.3) return 2;
  if (x < 1.6) return 3;
  if (x < 2.0) return 4;
  return 5;
}

export const HEAT_BINS = ["< 1.05x", "1.05 to 1.15x", "1.15 to 1.3x", "1.3 to 1.6x", "1.6 to 2x", "2x or more"];

export function policy(name: string): Policy {
  return data.policies.find((p) => p.name === name)!;
}
