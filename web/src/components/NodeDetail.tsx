"use client";

import StepChart from "@/components/StepChart";
import {
  ACTION_LABEL,
  data,
  peerMedianSeries,
  rankOfNode,
  REASON_LABEL,
  REASON_VAR,
  type Verdict,
} from "@/lib/data";

const PLANTED: Record<string, string> = {
  [data.meta.planted.badNode]: "Planted problem: the slowed worker in trace AR. This is the bad node.",
  [data.meta.planted.sdcNode]: "Planted problem (synthetic): a chip that corrupts training while passing idle checks.",
  [data.meta.planted.decoyNode]: "Planted decoy (synthetic): one slow reading in one old job. Not enough to call it a lemon.",
};

export default function NodeDetail({ node, verdict, withHistory }: { node: string; verdict?: Verdict; withHistory: boolean }) {
  const found = rankOfNode(node);
  if (!found) return null;
  const { job, rank } = found;
  const peers = peerMedianSeries(job, rank);
  const hist = data.history[node];
  const shownObs = hist?.observations.filter((o) => withHistory || o.current) ?? [];
  const c = verdict?.condition;

  return (
    <div className="rounded-xl border border-line bg-surface p-4 sm:p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-xl font-semibold tnum">{node}</h3>
        <span className="text-sm text-muted">
          {job.id}, stage {rank.stage}, replica {rank.dp}
        </span>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {c ? (
          <>
            <span className="inline-flex items-center gap-2 rounded-md border border-line px-2.5 py-1 text-sm font-medium">
              <span className="inline-block w-3 h-3 rounded-[3px]" style={{ background: REASON_VAR[c.reason] }} />
              {REASON_LABEL[c.reason]}
              <span className="font-mono text-xs text-muted">{c.reason}</span>
            </span>
            <span className="text-xs text-muted">
              owner: <span className="text-ink-2">{c.attributedTo}</span>, confidence:{" "}
              <span className="text-ink-2">{c.confidence}</span>
            </span>
          </>
        ) : (
          <span className="inline-flex items-center gap-2 rounded-md border border-line px-2.5 py-1 text-sm">
            <span className="inline-block w-3 h-3 rounded-[3px] bg-surface-2 border border-line" />
            No verdict
          </span>
        )}
      </div>

      <p className="mt-3 text-sm text-ink">
        {c
          ? c.message
          : "No rule fired. That means no evidence, not a clean bill of health. The engine never reports \"healthy\"."}
      </p>
      {verdict && (
        <p className="mt-2 text-sm">
          <span className="text-muted">Action: </span>
          <strong>{ACTION_LABEL[verdict.action.kind] ?? verdict.action.kind}</strong>
          <span className="text-ink-2">. {verdict.action.detail}</span>
        </p>
      )}
      {PLANTED[node] && <p className="mt-2 text-xs text-muted">{PLANTED[node]}</p>}

      <h4 className="mt-5 text-xs font-semibold uppercase tracking-wide text-muted">Step timing, real trace {job.trace}</h4>
      <div className="mt-2">
        <StepChart
          steps={job.steps}
          mine={rank.computeS}
          peers={peers}
          label={`${node} compute time per step against the median of its stage peers`}
        />
      </div>
      <dl className="mt-2 grid grid-cols-3 gap-2 text-center">
        <Stat label="vs stage peers" value={`${rank.peerRatio.toFixed(2)}x`} />
        <Stat label="steps slow vs peers" value={`${Math.round(rank.persistence * 100)}%`} />
        <Stat label="vs job median" value={`${rank.vsJobMedian.toFixed(2)}x`} />
      </dl>

      {c && c.evidence.length > 0 && (
        <>
          <h4 className="mt-5 text-xs font-semibold uppercase tracking-wide text-muted">Evidence</h4>
          <table className="mt-2 w-full text-sm">
            <tbody>
              {c.evidence.map((e) => (
                <tr key={e.signal} className="border-t border-line">
                  <td className="py-1.5 pr-2 font-mono text-xs">{e.signal}</td>
                  <td className="py-1.5 pr-2 tnum font-medium">{e.value}</td>
                  <td className="py-1.5 text-xs text-ink-2">{e.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <h4 className="mt-5 text-xs font-semibold uppercase tracking-wide text-muted">
        History across jobs <span className="normal-case font-normal">(synthetic{withHistory ? "" : ", earlier jobs hidden"})</span>
      </h4>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full text-xs tnum">
          <thead className="text-muted">
            <tr>
              <th className="text-left font-normal py-1 pr-2">job</th>
              <th className="text-right font-normal py-1 pr-2">vs peers</th>
              <th className="text-left font-normal py-1 pr-2">outlier</th>
              <th className="text-right font-normal py-1 pr-2">anomalies</th>
              <th className="text-left font-normal py-1 pr-2">other signals</th>
              <th className="text-left font-normal py-1">idle check</th>
            </tr>
          </thead>
          <tbody>
            {shownObs.map((o) => (
              <tr key={o.job} className="border-t border-line">
                <td className="py-1 pr-2">
                  {o.job}
                  {o.current && <span className="ml-1 text-muted">(now)</span>}
                </td>
                <td className="py-1 pr-2 text-right">{o.peerRatio == null ? "" : `${o.peerRatio.toFixed(2)}x`}</td>
                <td className="py-1 pr-2">{o.persistentOutlier ? "yes" : ""}</td>
                <td className="py-1 pr-2 text-right">{o.anomalyEvents || ""}</td>
                <td className="py-1 pr-2 text-ink-2">
                  {[
                    o.excludedByJob && "excluded by job",
                    o.repairTickets > 0 && `${o.repairTickets} ticket`,
                    o.multiNodeFailure && "multi-node failure",
                  ]
                    .filter(Boolean)
                    .join(", ")}
                </td>
                <td className="py-1">{o.activeCheckPassed == null ? "not run" : o.activeCheckPassed ? "pass" : "fail"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {verdict && (
        <details className="mt-5 group">
          <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide text-muted hover:text-ink">
            Node condition JSON
          </summary>
          <pre className="mt-2 overflow-x-auto rounded-lg bg-surface-2 p-3 text-[11px] leading-relaxed font-mono">
            {JSON.stringify({ ...verdict, action: undefined }, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-surface-2 px-2 py-2">
      <dd className="text-base font-semibold tnum">{value}</dd>
      <dt className="text-[11px] text-muted leading-tight">{label}</dt>
    </div>
  );
}
