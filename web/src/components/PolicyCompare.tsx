import { data, POLICY_LABEL, type Policy } from "@/lib/data";

const yes = (b: boolean) => (b ? "Yes" : "No");
const pct = (x: number) => `${(100 * x).toFixed(1)}%`;

interface Row {
  label: string;
  hint?: string;
  get: (p: Policy) => string;
  better?: (p: Policy) => boolean;
}

export default function PolicyCompare() {
  const ps = data.policies;
  const nJobs = data.jobs.length;
  const counts: Row[] = [
    { label: "Healthy nodes replaced", get: (p) => String(p.healthyReplaced.length), better: (p) => p.healthyReplaced.length === 0 },
    { label: `Spares used (of ${data.meta.spares})`, get: (p) => String(p.sparesUsed) },
    { label: "Flagged nodes left with no spare", get: (p) => String(p.flaggedUnserved), better: (p) => p.flaggedUnserved === 0 },
    { label: "Bad node fixed", get: (p) => yes(p.badNodeFixed), better: (p) => p.badNodeFixed },
    { label: "Corrupting chip pulled", get: (p) => yes(p.sdcPulled), better: (p) => p.sdcPulled },
    {
      label: `Slow jobs given the right owner`,
      hint: `of ${nJobs}`,
      get: (p) => `${p.jobsRightOwner.length}`,
      better: (p) => p.jobsRightOwner.length === nJobs,
    },
  ];
  const goodput: Row[] = [
    { label: "Goodput, node-weighted", get: (p) => pct(p.goodput) },
    ...data.jobs.map((j) => ({ label: `  ${j.id}`, get: (p: Policy) => pct(p.goodputByJob[j.id]) })),
  ];

  return (
    <div>
      <div className="overflow-x-auto rounded-xl border border-line bg-surface">
        <table className="w-full min-w-[640px] text-sm tnum">
          <thead>
            <tr className="border-b border-line align-bottom">
              <th className="text-left font-normal text-muted p-3 w-[34%]">Same pool, same three jobs</th>
              {ps.map((p) => (
                <th
                  key={p.name}
                  className={`text-left p-3 align-bottom ${p.name === "attributed" ? "bg-accent-soft" : ""}`}
                >
                  <div className="font-semibold">{POLICY_LABEL[p.name].title}</div>
                  <div className="font-normal text-xs text-muted leading-snug">{POLICY_LABEL[p.name].blurb}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {counts.map((r) => (
              <TRow key={r.label} row={r} ps={ps} />
            ))}
            <tr>
              <td colSpan={ps.length + 1} className="px-3 pt-4 pb-1 text-xs text-muted border-t border-line-strong">
                Below this line depends on assumptions: repair acts after {100 * data.simParams.act_at}% of the run, a
                checkpoint every {data.simParams.ckpt_interval_steps} steps, a restart costs{" "}
                {data.simParams.restart_steps} steps. Above it does not.
              </td>
            </tr>
            {goodput.map((r) => (
              <TRow key={r.label} row={r} ps={ps} muted={r.label.startsWith("  ")} />
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <Takeaway title="Against naive repair">
          Naive repair burns all {data.meta.spares} spares, three of them on healthy nodes, and still leaves three
          flagged nodes waiting. It never sees the chip. But naive is a straw man, so I do not lead with it.
        </Takeaway>
        <Takeaway title="Against a good detector">
          Comparing each rank to its stage peers already stops the waste of healthy nodes. What Node Verdict adds is
          the corrupting chip, which timing cannot see, and a named owner for every slow job: 3 of 3, against 1 of 3.
        </Takeaway>
        <Takeaway title="What it does not add">
          Goodput. Nearly all of the gain is checkpoint timing and peer comparison, which any good system can do. Node
          Verdict scores {Math.abs(data.sensitivity[1].vsPeerAware).toFixed(1)} points below peer-aware: pulling the
          chip costs a restart, and this model does not price corrupted training.
        </Takeaway>
      </div>

      <h3 className="mt-8 font-semibold">Where the goodput gain comes from</h3>
      <p className="text-sm text-ink-2 mt-1 max-w-3xl">
        Goodput gain of Node Verdict over each policy, in percentage points, at three checkpoint intervals. The first
        column grows with the interval because naive repair restarts mid-run and loses up to half an interval of work.
      </p>
      <div className="mt-3 overflow-x-auto rounded-xl border border-line bg-surface">
        <table className="w-full min-w-[480px] text-sm tnum">
          <thead>
            <tr className="border-b border-line text-left">
              <th className="p-3 font-normal text-muted">Checkpoint every</th>
              <th className="p-3 font-semibold">vs naive</th>
              <th className="p-3 font-semibold">vs naive + checkpoint</th>
              <th className="p-3 font-semibold">vs peer-aware</th>
            </tr>
          </thead>
          <tbody>
            {data.sensitivity.map((s) => (
              <tr key={s.ckptSteps} className="border-t border-line">
                <td className="p-3 text-ink-2">{s.ckptSteps} steps</td>
                <td className="p-3">{signed(s.vsNaive)}</td>
                <td className="p-3">{signed(s.vsNaiveCheckpoint)}</td>
                <td className="p-3">{signed(s.vsPeerAware)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TRow({ row, ps, muted }: { row: Row; ps: Policy[]; muted?: boolean }) {
  return (
    <tr className="border-t border-line">
      <td className={`p-3 ${muted ? "text-muted pl-6" : ""}`}>
        {row.label.trim()} {row.hint && <span className="text-muted text-xs">{row.hint}</span>}
      </td>
      {ps.map((p) => {
        const good = row.better?.(p);
        return (
          <td
            key={p.name}
            className={`p-3 ${p.name === "attributed" ? "bg-accent-soft font-semibold" : ""} ${muted ? "text-muted" : ""}`}
          >
            {row.get(p)}
            {row.better && (
              <span className={`ml-1.5 text-xs ${good ? "text-good" : "text-bad"}`} aria-label={good ? "good" : "bad"}>
                {good ? "✓" : "✗"}
              </span>
            )}
          </td>
        );
      })}
    </tr>
  );
}

function Takeaway({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-4">
      <h4 className="font-semibold text-sm">{title}</h4>
      <p className="mt-1.5 text-sm text-ink-2 leading-relaxed">{children}</p>
    </div>
  );
}

function signed(x: number): string {
  return `${x >= 0 ? "+" : "−"}${Math.abs(x).toFixed(1)} pts`;
}
