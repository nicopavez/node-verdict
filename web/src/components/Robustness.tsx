import { data, type Band } from "@/lib/data";

const NAMES: Record<string, { label: string; what: string }> = {
  peer_threshold: { label: "Peer threshold", what: "how much slower than stage peers counts as slow" },
  persistence_min: { label: "Persistence", what: "share of steps that must be slow" },
  stage_threshold: { label: "Stage threshold", what: "how much slower than the job a stage must be" },
  lemon_min_score: { label: "Lemon score", what: "weighted history needed to call a lemon" },
  lemon_min_jobs: { label: "Lemon jobs", what: "distinct jobs where the node was slow" },
  sdc_min_jobs: { label: "Corruption jobs", what: "distinct jobs with training anomalies" },
};

const INT = new Set(["lemon_min_score", "lemon_min_jobs", "sdc_min_jobs"]);

export default function Robustness() {
  const { bands, healthyNodesEverChanged } = data.robustness;
  return (
    <div>
      <div className="rounded-xl border border-line bg-surface divide-y divide-[var(--border)]">
        {bands.map((b) => (
          <BandRow key={b.param} b={b} />
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-xs text-ink-2">
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-5 h-1.5 rounded-full" style={{ background: "var(--grid)" }} />
          Range tested
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-5 h-1.5 rounded-full" style={{ background: "var(--accent)" }} />
          Every verdict stays the same
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full border-2" style={{ borderColor: "var(--ink)", background: "var(--surface)" }} />
          Default
        </span>
      </div>
      <p className="mt-4 text-sm text-ink-2 max-w-3xl">
        Healthy nodes replaced or pulled at any setting tested:{" "}
        <strong className="text-ink tnum">{healthyNodesEverChanged}</strong>. The stage threshold is the one that
        matters, and both of its edges fail safe: too low and a healthy stage is blamed on the job, too high and a slow
        stage goes unexplained. Neither changes a node.
      </p>
    </div>
  );
}

function BandRow({ b }: { b: Band }) {
  const n = NAMES[b.param];
  const f = (x: number) => (INT.has(b.param) ? String(x) : x.toFixed(2));
  const span = b.grid_max - b.grid_min;
  const pos = (x: number) => `${((x - b.grid_min) / span) * 100}%`;
  return (
    <div className="grid gap-3 p-4 md:grid-cols-[13rem_1fr_16rem] md:items-center">
      <div>
        <div className="font-semibold text-sm">
          {n.label} <span className="font-mono text-xs font-normal text-muted">default {f(b.default)}</span>
        </div>
        <div className="text-xs text-muted">{n.what}</div>
        <div className="text-[11px] text-muted mt-0.5">tested on {b.basis}</div>
      </div>

      <div className="px-1">
        <div className="relative h-6" role="img" aria-label={`${n.label}: verdicts unchanged from ${f(b.low)} to ${f(b.high)}, default ${f(b.default)}`}>
          <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-1.5 rounded-full" style={{ background: "var(--grid)" }} />
          <div
            className="absolute top-1/2 -translate-y-1/2 h-1.5 rounded-full"
            style={{ left: pos(b.low), width: `calc(${pos(b.high)} - ${pos(b.low)})`, background: "var(--accent)" }}
          />
          <div
            className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 w-3 h-3 rounded-full border-2"
            style={{ left: pos(b.default), borderColor: "var(--ink)", background: "var(--surface)" }}
          />
        </div>
        <div className="relative h-4 text-[10px] text-muted tnum">
          <span className="absolute left-0">{f(b.grid_min)}</span>
          <span className="absolute right-0">{f(b.grid_max)}</span>
          <span className="absolute -translate-x-1/2 text-ink-2 font-medium" style={{ left: pos(b.low) }}>
            {b.low !== b.grid_min ? f(b.low) : ""}
          </span>
          <span className="absolute -translate-x-1/2 text-ink-2 font-medium" style={{ left: pos(b.high) }}>
            {b.high !== b.grid_max ? f(b.high) : ""}
          </span>
        </div>
      </div>

      <div className="text-xs text-ink-2 leading-relaxed">
        {b.below && (
          <div>
            <span className="text-muted">Below {f(b.low)}:</span> {b.below}
          </div>
        )}
        {b.above && (
          <div>
            <span className="text-muted">Above {f(b.high)}:</span> {b.above}
          </div>
        )}
        {!b.below && !b.above && <div className="text-muted">No change anywhere in the range tested.</div>}
      </div>
    </div>
  );
}
