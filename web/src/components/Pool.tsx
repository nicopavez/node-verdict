"use client";

import { useState } from "react";
import {
  data,
  heatLevel,
  HEAT_BINS,
  REASON_LABEL,
  REASON_SHORT,
  REASON_VAR,
  type Job,
  type Rank,
  type Reason,
  type Verdict,
} from "@/lib/data";

export type Mode = "slowness" | "verdict";

interface Props {
  mode: Mode;
  setMode: (m: Mode) => void;
  withHistory: boolean;
  setWithHistory: (b: boolean) => void;
  verdicts: Map<string, Verdict>;
  selected: string;
  onSelect: (node: string) => void;
}

interface Hover {
  x: number;
  y: number;
  job: Job;
  rank: Rank;
}

export default function Pool({ mode, setMode, withHistory, setWithHistory, verdicts, selected, onSelect }: Props) {
  const [hover, setHover] = useState<Hover | null>(null);
  const shown = new Set<Reason>([...verdicts.values()].map((v) => v.condition.reason));

  return (
    <div className="relative">
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <Segmented
          label="View"
          value={mode}
          onChange={(v) => setMode(v as Mode)}
          options={[
            { value: "slowness", label: "1. What a monitor sees" },
            { value: "verdict", label: "2. What Node Verdict says" },
          ]}
        />
        {mode === "verdict" && (
          <Segmented
            label="Cross-job history"
            value={withHistory ? "on" : "off"}
            onChange={(v) => setWithHistory(v === "on")}
            options={[
              { value: "on", label: "History on" },
              { value: "off", label: "History off" },
            ]}
          />
        )}
      </div>

      <p className="text-sm text-ink-2 mb-4 max-w-3xl min-h-[2.5rem]">
        {mode === "slowness" ? (
          <>
            Each square is a node, laid out by pipeline stage (rows) and data-parallel replica (columns). Shade is
            how slow the node runs against the job&apos;s median node: the comparison a naive monitor makes.{" "}
            <strong className="text-ink">Seven nodes look slow. Only one of them is broken, and the chip that is
            broken does not look slow at all.</strong>
          </>
        ) : withHistory ? (
          <>
            Node Verdict compares each node to its stage peers and checks its history across other jobs.{" "}
            <strong className="text-ink">One bad node, one corrupting chip, and two jobs whose slowdown is the
            customer&apos;s setup.</strong> The other 24 nodes get no verdict. No verdict is not the same as healthy.
          </>
        ) : (
          <>
            Without history across jobs, the engine can only see this job.{" "}
            <strong className="text-ink">N00 drops to a suspect, so nothing is replaced yet, and the corrupting chip
            is invisible.</strong> This is why the cloud, which sees every job a node has run, should own the call.
          </>
        )}
      </p>

      <div className="flex flex-wrap gap-4 items-start">
        {data.jobs.map((job) => (
          <JobGrid
            key={job.id}
            job={job}
            mode={mode}
            withHistory={withHistory}
            verdicts={verdicts}
            selected={selected}
            onSelect={onSelect}
            onHover={setHover}
          />
        ))}
      </div>

      <Legend mode={mode} shown={shown} />

      {hover && <Tooltip hover={hover} verdict={verdicts.get(hover.rank.node)} />}
    </div>
  );
}

function JobGrid({
  job,
  mode,
  withHistory,
  verdicts,
  selected,
  onSelect,
  onHover,
}: {
  job: Job;
  mode: Mode;
  withHistory: boolean;
  verdicts: Map<string, Verdict>;
  selected: string;
  onSelect: (n: string) => void;
  onHover: (h: Hover | null) => void;
}) {
  const cols = job.dps.length;
  const owner: "node" | "job" | "none" = (withHistory ? data.ownerByJob.withHistory : data.ownerByJob.noHistory)[job.id] ?? "none";
  return (
    <section className="rounded-xl border border-line bg-surface p-3 sm:p-4 max-w-full">
      <header className="flex items-baseline justify-between gap-2 mb-1">
        <h3 className="font-semibold">
          {job.id} <span className="font-normal text-muted">trace {job.trace}</span>
        </h3>
        <span className="text-xs text-muted tnum">{job.slowdown.toFixed(2)}x slower than ideal</span>
      </header>
      <p className="text-xs text-muted mb-3">
        Actual cause: <span className="text-ink-2">{job.traceLabel.toLowerCase()}</span>
      </p>

      <div className="grid gap-[2px]" style={{ gridTemplateColumns: `2.25rem repeat(${cols}, 3.25rem)` }}>
        <div />
        {job.dps.map((d) => (
          <div key={d} className="text-[10px] text-muted text-center pb-1 leading-tight">
            rep {d}
          </div>
        ))}
        {job.stages.map((s) => (
          <Row key={s}>
            <div className="text-[10px] text-muted self-center leading-tight">
              stage
              <br />
              {s}
            </div>
            {job.dps.map((d) => {
              const rank = job.ranks.find((r) => r.stage === s && r.dp === d)!;
              return (
                <Cell
                  key={d}
                  job={job}
                  rank={rank}
                  mode={mode}
                  verdict={verdicts.get(rank.node)}
                  selected={selected === rank.node}
                  onSelect={onSelect}
                  onHover={onHover}
                />
              );
            })}
          </Row>
        ))}
      </div>

      <footer className="mt-3 text-xs min-h-[1.25rem]">
        {mode === "verdict" ? (
          <span className="text-ink-2">
            Owner of the slowdown:{" "}
            <strong className="text-ink">
              {owner === "node" ? "the node" : owner === "job" ? "the customer's job" : "no call yet"}
            </strong>
            {owner !== "none" && (owner === (job.cause === "node" ? "node" : "job") ? " (correct)" : " (wrong)")}
          </span>
        ) : (
          <span className="text-muted">
            Slowest stage: {maxStage(job).toFixed(2)}x the job median
          </span>
        )}
      </footer>
    </section>
  );
}

function Row({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}

function Cell({
  job,
  rank,
  mode,
  verdict,
  selected,
  onSelect,
  onHover,
}: {
  job: Job;
  rank: Rank;
  mode: Mode;
  verdict?: Verdict;
  selected: boolean;
  onSelect: (n: string) => void;
  onHover: (h: Hover | null) => void;
}) {
  let bg = "var(--surface-2)";
  let ink = "var(--ink-2)";
  let sub = "";
  if (mode === "slowness") {
    const lvl = heatLevel(rank.vsJobMedian);
    bg = `var(--heat-${lvl})`;
    ink = lvl >= 3 ? "var(--heat-ink-dark)" : "var(--heat-ink-light)";
    sub = `${rank.vsJobMedian.toFixed(2)}x`;
  } else if (verdict) {
    bg = REASON_VAR[verdict.condition.reason];
    ink = "var(--v-on-fill)";
    sub = REASON_SHORT[verdict.condition.reason];
  } else {
    sub = "none";
  }
  const label = `${rank.node}, ${job.id} stage ${rank.stage} replica ${rank.dp}: ${
    mode === "slowness"
      ? `${rank.vsJobMedian.toFixed(2)} times the job median`
      : verdict
        ? REASON_LABEL[verdict.condition.reason]
        : "no verdict"
  }`;
  return (
    <button
      type="button"
      aria-label={label}
      aria-pressed={selected}
      onClick={() => onSelect(rank.node)}
      onMouseMove={(e) => onHover({ x: e.clientX, y: e.clientY, job, rank })}
      onMouseLeave={() => onHover(null)}
      onFocus={(e) => {
        const r = e.currentTarget.getBoundingClientRect();
        onHover({ x: r.right, y: r.top, job, rank });
      }}
      onBlur={() => onHover(null)}
      className="relative w-[3.25rem] h-[3.25rem] rounded-[4px] flex flex-col items-center justify-center transition-[box-shadow] duration-100 cursor-pointer"
      style={{
        background: bg,
        color: ink,
        boxShadow: selected ? "0 0 0 2px var(--surface), 0 0 0 4px var(--ink)" : undefined,
      }}
    >
      <span className="text-[11px] sm:text-xs font-semibold tnum leading-none">{rank.node}</span>
      <span className="text-[10px] sm:text-[11px] leading-none mt-1 tnum opacity-90">{sub}</span>
    </button>
  );
}

function Tooltip({ hover, verdict }: { hover: Hover; verdict?: Verdict }) {
  const { rank, job } = hover;
  const left = typeof window !== "undefined" ? Math.min(hover.x + 14, window.innerWidth - 250) : hover.x;
  return (
    <div
      role="tooltip"
      className="pointer-events-none fixed z-50 w-60 rounded-lg border border-line bg-surface shadow-lg p-3 text-xs"
      style={{ left, top: hover.y + 14 }}
    >
      <div className="font-semibold text-sm mb-1">
        {rank.node} <span className="font-normal text-muted">{job.id}, stage {rank.stage}, replica {rank.dp}</span>
      </div>
      <dl className="grid grid-cols-[1fr_auto] gap-x-3 gap-y-0.5 tnum">
        <dt className="text-muted">vs job median</dt>
        <dd>{rank.vsJobMedian.toFixed(2)}x</dd>
        <dt className="text-muted">vs stage peers</dt>
        <dd>{rank.peerRatio.toFixed(2)}x</dd>
        <dt className="text-muted">steps slow vs peers</dt>
        <dd>{Math.round(rank.persistence * 100)}%</dd>
        <dt className="text-muted">verdict</dt>
        <dd>{verdict ? REASON_LABEL[verdict.condition.reason] : "none"}</dd>
      </dl>
      <div className="text-muted mt-1.5">Click for evidence</div>
    </div>
  );
}

function Legend({ mode, shown }: { mode: Mode; shown: Set<Reason> }) {
  if (mode === "slowness") {
    return (
      <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-ink-2">
        <span className="text-muted">Node time vs job median:</span>
        {HEAT_BINS.map((b, i) => (
          <span key={b} className="inline-flex items-center gap-1.5">
            <span className="inline-block w-3.5 h-3.5 rounded-[3px]" style={{ background: `var(--heat-${i})` }} />
            {b}
          </span>
        ))}
      </div>
    );
  }
  const order: Reason[] = ["NodeLemon", "SDCSuspect", "NodeSuspect", "WorkloadImbalance"];
  return (
    <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-ink-2">
      {order
        .filter((r) => shown.has(r))
        .map((r) => (
          <span key={r} className="inline-flex items-center gap-1.5">
            <span className="inline-block w-3.5 h-3.5 rounded-[3px]" style={{ background: REASON_VAR[r] }} />
            <span>
              {REASON_LABEL[r]} <span className="text-muted font-mono">{r}</span>
            </span>
          </span>
        ))}
      <span className="inline-flex items-center gap-1.5">
        <span className="inline-block w-3.5 h-3.5 rounded-[3px] bg-surface-2 border border-line" />
        No verdict
      </span>
    </div>
  );
}

export function Segmented({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex rounded-lg border border-line bg-surface p-0.5">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          onClick={() => onChange(o.value)}
          className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
            value === o.value ? "bg-ink text-page font-medium" : "text-ink-2 hover:bg-surface-2"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function maxStage(job: Job): number {
  return Math.max(...Object.values(job.stageRatio));
}
