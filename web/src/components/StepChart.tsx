"use client";

import { useRef, useState } from "react";

interface Props {
  steps: number[];
  mine: number[];
  peers: number[];
  label: string;
}

const W = 400;
const H = 160;
const PAD = { l: 40, r: 58, t: 10, b: 24 };

/** One rank's compute time per step against the median of its stage peers. One axis, two series. */
export default function StepChart({ steps, mine, peers, label }: Props) {
  const ref = useRef<SVGSVGElement>(null);
  const [hi, setHi] = useState<number | null>(null);

  const all = [...mine, ...peers];
  const lo = 0;
  const top = niceMax(Math.max(...all));
  const x = (i: number) => PAD.l + (i / Math.max(1, steps.length - 1)) * (W - PAD.l - PAD.r);
  const y = (v: number) => PAD.t + (1 - (v - lo) / (top - lo)) * (H - PAD.t - PAD.b);
  const path = (s: number[]) => s.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");
  const ticks = [0, top / 2, top];

  function move(e: React.PointerEvent<SVGSVGElement>) {
    const box = ref.current!.getBoundingClientRect();
    const px = ((e.clientX - box.left) / box.width) * W;
    const i = Math.round(((px - PAD.l) / (W - PAD.l - PAD.r)) * (steps.length - 1));
    setHi(Math.max(0, Math.min(steps.length - 1, i)));
  }

  const lastMine = mine[mine.length - 1];
  const lastPeers = peers[peers.length - 1];
  // End labels: if the lines finish close together, push the labels apart so they never overlap.
  const gap = 14;
  let yMine = y(lastMine);
  let yPeers = y(lastPeers);
  if (Math.abs(yMine - yPeers) < gap) {
    const mid = (yMine + yPeers) / 2;
    const mineAbove = lastMine >= lastPeers;
    yMine = mid + (mineAbove ? -gap / 2 : gap / 2);
    yPeers = mid + (mineAbove ? gap / 2 : -gap / 2);
  }

  return (
    <figure className="relative">
      <figcaption className="sr-only">{label}</figcaption>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-2 mb-1">
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-4 h-[2px]" style={{ background: "var(--s1)" }} />
          This node
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-4 h-[2px]" style={{ background: "var(--s2)" }} />
          Median of its stage peers
        </span>
      </div>
      <svg
        ref={ref}
        viewBox={`0 0 ${W} ${H}`}
        className="w-full h-auto touch-none select-none"
        role="img"
        aria-label={label}
        onPointerMove={move}
        onPointerDown={move}
        onPointerLeave={() => setHi(null)}
      >
        {ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.l} x2={W - PAD.r} y1={y(t)} y2={y(t)} stroke={t === 0 ? "var(--baseline)" : "var(--grid)"} strokeWidth={1} />
            <text x={PAD.l - 6} y={y(t)} dy="0.32em" textAnchor="end" fontSize={12} fill="var(--muted)" className="tnum">
              {fmtS(t)}
            </text>
          </g>
        ))}
        <text x={PAD.l} y={H - 6} fontSize={12} fill="var(--muted)">
          step {steps[0]}
        </text>
        <text x={W - PAD.r} y={H - 6} fontSize={12} fill="var(--muted)" textAnchor="end">
          step {steps[steps.length - 1]}
        </text>

        <path d={path(peers)} fill="none" stroke="var(--s2)" strokeWidth={2} strokeLinejoin="round" />
        <path d={path(mine)} fill="none" stroke="var(--s1)" strokeWidth={2} strokeLinejoin="round" />

        <text x={W - PAD.r + 6} y={yMine} dy="0.32em" fontSize={12} fill="var(--ink-2)">
          this node
        </text>
        <text x={W - PAD.r + 6} y={yPeers} dy="0.32em" fontSize={12} fill="var(--ink-2)">
          peers
        </text>

        {hi !== null && (
          <g>
            <line x1={x(hi)} x2={x(hi)} y1={PAD.t} y2={H - PAD.b} stroke="var(--baseline)" strokeWidth={1} />
            <circle cx={x(hi)} cy={y(peers[hi])} r={4} fill="var(--s2)" stroke="var(--surface)" strokeWidth={2} />
            <circle cx={x(hi)} cy={y(mine[hi])} r={4} fill="var(--s1)" stroke="var(--surface)" strokeWidth={2} />
          </g>
        )}
      </svg>
      {hi !== null && (
        <div
          className="pointer-events-none absolute top-6 rounded-md border border-line bg-surface shadow-md px-2.5 py-1.5 text-xs tnum"
          style={{ left: `${Math.min(70, (x(hi) / W) * 100)}%` }}
        >
          <div className="font-semibold">Step {steps[hi]}</div>
          <div>This node: {fmtS(mine[hi])}</div>
          <div>Peers: {fmtS(peers[hi])}</div>
          <div className="text-muted">{(mine[hi] / peers[hi]).toFixed(2)}x peers</div>
        </div>
      )}
    </figure>
  );
}

function niceMax(v: number): number {
  const p = Math.pow(10, Math.floor(Math.log10(v)));
  for (const m of [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) if (m * p >= v) return m * p;
  return 10 * p;
}

function fmtS(v: number): string {
  return v >= 10 ? `${v.toFixed(0)}s` : v >= 1 ? `${v.toFixed(1)}s` : `${v.toFixed(2)}s`;
}
