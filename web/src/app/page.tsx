"use client";

import { useMemo, useState } from "react";
import NodeDetail from "@/components/NodeDetail";
import PolicyCompare from "@/components/PolicyCompare";
import Pool, { type Mode } from "@/components/Pool";
import Robustness from "@/components/Robustness";
import { ACTION_LABEL, data, policy, REASON_LABEL, REASON_VAR, verdictMap } from "@/lib/data";

const REPO = "https://github.com/nicopavez/node-verdict";

export default function Home() {
  const [mode, setMode] = useState<Mode>("slowness");
  const [withHistory, setWithHistory] = useState(true);
  const [selected, setSelected] = useState(data.meta.planted.badNode);
  const verdicts = useMemo(() => verdictMap(mode === "slowness" ? true : withHistory), [mode, withHistory]);
  const detailVerdicts = useMemo(() => verdictMap(withHistory), [withHistory]);

  function select(node: string) {
    setSelected(node);
    // On narrow screens the detail panel sits below the grid. Bring it into view.
    if (window.matchMedia("(max-width: 1023px)").matches) {
      requestAnimationFrame(() => document.getElementById("node-detail")?.scrollIntoView({ behavior: "smooth", block: "start" }));
    }
  }

  return (
    <>
      <TopBar />
      <main className="mx-auto max-w-6xl px-4 sm:px-6">
        <Hero />

        <Section
          id="pool"
          kicker="The demo"
          title="A 32-node pool, three real training jobs, four hidden problems"
          lede="Timing comes from real ByteDance training traces. Node history is synthetic and labeled. Click any node."
        >
          <div className="grid gap-6 grid-cols-[minmax(0,1fr)] lg:grid-cols-[minmax(0,1fr)_25rem] lg:items-start">
            <Pool
              mode={mode}
              setMode={setMode}
              withHistory={withHistory}
              setWithHistory={setWithHistory}
              verdicts={verdicts}
              selected={selected}
              onSelect={select}
            />
            <div id="node-detail" className="lg:sticky lg:top-16 scroll-mt-14">
              <NodeDetail node={selected} verdict={detailVerdicts.get(selected)} withHistory={withHistory} />
            </div>
          </div>
        </Section>

        <Section
          id="how"
          kicker="How it decides"
          title="Three rules, in order. The first one that fires wins."
          lede="No model in the decision path. Every verdict can be explained, reproduced, and tuned by editing one threshold."
        >
          <HowItWorks />
        </Section>

        <Section
          id="compare"
          kicker="Is it worth it"
          title="Four repair policies on the same pool"
          lede="Two of the four are controls, so Node Verdict gets no credit it did not earn."
        >
          <PolicyCompare />
        </Section>

        <Section
          id="robustness"
          kicker="How fragile is it"
          title="How far each threshold can move before a verdict changes"
          lede="The thresholds were set by hand on three traces, with no held-out data. So I swept each one on its own."
        >
          <Robustness />
          <p className="mt-3 text-sm text-ink-2 max-w-3xl">
            This does not validate the thresholds for a real fleet. The peer threshold looks robust because the planted
            slow worker runs 2.35x its peers. A degraded node in production may run 1.1x, which is where the threshold
            would really be tested.
          </p>
        </Section>

        <Section
          id="api"
          kicker="The contract"
          title="A verdict is a Kubernetes-style node condition"
          lede="Customers will automate against these reason codes, so they are an API. A test pins all four. A rename is a breaking change."
        >
          <ApiTable />
        </Section>

        <Section id="limits" kicker="Honest limits" title="What is real, what is synthetic, and what this does not prove">
          <Limits />
        </Section>
      </main>
      <Footer />
    </>
  );
}

function TopBar() {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-page/90 backdrop-blur">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 h-12 flex items-center justify-between gap-4">
        <a href="#top" className="font-semibold tracking-tight">
          Node Verdict
        </a>
        <nav className="flex items-center gap-4 text-sm text-ink-2">
          <a className="hidden sm:inline hover:text-ink" href="#pool">Demo</a>
          <a className="hidden sm:inline hover:text-ink" href="#compare">Results</a>
          <a className="hidden md:inline hover:text-ink" href="#robustness">Robustness</a>
          <a className="hidden md:inline hover:text-ink" href="#limits">Limits</a>
          <a className="hover:text-ink font-medium text-ink" href={REPO}>
            GitHub
          </a>
        </nav>
      </div>
    </header>
  );
}

function Hero() {
  const naive = policy("naive");
  const peer = policy("peer-aware");
  const nv = policy("attributed");
  const n = data.jobs.length;
  const tiles = [
    { label: "Healthy nodes replaced", before: String(naive.healthyReplaced.length), after: String(nv.healthyReplaced.length), peer: String(peer.healthyReplaced.length) },
    { label: `Spares used, of ${data.meta.spares}`, before: String(naive.sparesUsed), after: String(nv.sparesUsed), peer: String(peer.sparesUsed) },
    { label: "Corrupting chip pulled", before: naive.sdcPulled ? "Yes" : "No", after: nv.sdcPulled ? "Yes" : "No", peer: peer.sdcPulled ? "Yes" : "No" },
    { label: "Slow jobs with the right owner", before: `${naive.jobsRightOwner.length} of ${n}`, after: `${nv.jobsRightOwner.length} of ${n}`, peer: `${peer.jobsRightOwner.length} of ${n}` },
  ];
  return (
    <section id="top" className="pt-10 sm:pt-16 pb-6">
      <p className="text-sm font-medium text-accent">GPU cloud data plane, product design</p>
      <h1 className="mt-2 text-3xl sm:text-5xl font-semibold tracking-tight leading-[1.1] max-w-4xl">
        When a GPU training job slows down, is it the node or the job?
      </h1>
      <p className="mt-4 text-lg text-ink-2 max-w-3xl leading-relaxed">
        Node Verdict answers that before anything gets replaced. It compares each worker to its pipeline-stage peers,
        checks the node&apos;s record across other customers&apos; jobs, and names an owner: the node, or the job. Then
        policy picks the action.
      </p>

      <div className="mt-8 grid grid-cols-2 lg:grid-cols-4 gap-3">
        {tiles.map((t) => (
          <div key={t.label} className="rounded-xl border border-line bg-surface p-4">
            <div className="text-xs text-muted">{t.label}</div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-3xl font-semibold">{t.after}</span>
              <span className="text-sm text-muted">
                vs <span className="line-through decoration-1">{t.before}</span> naive
              </span>
            </div>
            <div className="mt-1 text-xs text-muted">peer-aware detector: {t.peer}</div>
          </div>
        ))}
      </div>
      <p className="mt-4 text-sm text-ink-2 max-w-3xl">
        Against naive repair it wins on every count. Against a good peer-aware detector it ties on healthy nodes, spends
        one more spare on purpose to pull the chip, and is the only policy that gives every slow job an owner. It does
        not improve goodput. <a href="#compare" className="text-accent hover:underline">See the full comparison.</a>
      </p>
    </section>
  );
}

function Section({
  id,
  kicker,
  title,
  lede,
  children,
}: {
  id: string;
  kicker: string;
  title: string;
  lede?: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="py-10 sm:py-14 border-t border-line scroll-mt-12">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted">{kicker}</p>
      <h2 className="mt-1 text-2xl sm:text-3xl font-semibold tracking-tight max-w-4xl">{title}</h2>
      {lede && <p className="mt-2 text-ink-2 max-w-3xl">{lede}</p>}
      <div className="mt-6">{children}</div>
    </section>
  );
}

function HowItWorks() {
  const cfg = data.config as Record<string, number>;
  const rules = [
    {
      n: 1,
      reason: "SDCSuspect" as const,
      rule: `Training anomalies in ${cfg.sdc_min_jobs} or more jobs, idle checks pass, timing is normal.`,
      why: "Slowness cannot explain wrong answers, so this runs first. It needs history: one job is not enough.",
    },
    {
      n: 2,
      reason: "NodeLemon" as const,
      alt: "NodeSuspect" as const,
      rule: `Slower than stage peers by ${cfg.peer_threshold}x in ${100 * cfg.persistence_min}% of steps or more. Lemon if history shows it in ${cfg.lemon_min_jobs}+ jobs, otherwise Suspect.`,
      why: "One job cannot separate a bad node from a bad position. A second job can. Only the cloud sees both.",
    },
    {
      n: 3,
      reason: "WorkloadImbalance" as const,
      rule: `The whole stage runs ${cfg.stage_threshold}x the job median or more, and this node matches its stage peers.`,
      why: "The slowdown follows the stage, not the node. Replacing hardware will not fix it. Tell the customer.",
    },
  ];
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {rules.map((r) => (
        <div key={r.n} className="rounded-xl border border-line bg-surface p-4">
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-ink text-page text-xs font-semibold flex items-center justify-center">{r.n}</span>
            <span className="inline-block w-3 h-3 rounded-[3px]" style={{ background: REASON_VAR[r.reason] }} />
            <span className="font-semibold text-sm">{REASON_LABEL[r.reason]}</span>
            {r.alt && (
              <>
                <span className="text-muted text-sm">or</span>
                <span className="inline-block w-3 h-3 rounded-[3px]" style={{ background: REASON_VAR[r.alt] }} />
                <span className="font-semibold text-sm">{REASON_LABEL[r.alt]}</span>
              </>
            )}
          </div>
          <p className="mt-3 text-sm">{r.rule}</p>
          <p className="mt-2 text-sm text-ink-2">{r.why}</p>
        </div>
      ))}
      <div className="md:col-span-3 rounded-xl border border-line bg-surface-2 p-4 text-sm text-ink-2">
        <strong className="text-ink">The key move is the comparison group.</strong> In job-b, stage 3 runs 1.63x the
        job median on every replica because the last stage carries the loss layer. Compare its nodes to the whole job and
        you replace two healthy machines. Compare them to their stage peers and they are normal, which is correct: the
        stage is slow, not the nodes. <strong className="text-ink">No match means no verdict.</strong> The engine never
        says &quot;healthy&quot;, because no evidence is not the same as good evidence.
      </div>
    </div>
  );
}

function ApiTable() {
  const example = data.verdicts.withHistory.find((v) => v.node === data.meta.planted.badNode)!;
  return (
    <div className="grid gap-6 grid-cols-[minmax(0,1fr)] lg:grid-cols-2 lg:items-start">
      <div className="overflow-x-auto rounded-xl border border-line bg-surface">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line text-left text-muted">
              <th className="p-3 font-normal">Reason code</th>
              <th className="p-3 font-normal">Owner</th>
              <th className="p-3 font-normal">Default action</th>
            </tr>
          </thead>
          <tbody>
            {data.reasonCodes.map((r) => (
              <tr key={r.code} className="border-t border-line align-top">
                <td className="p-3">
                  <div className="flex items-center gap-2">
                    <span className="inline-block w-3 h-3 rounded-[3px]" style={{ background: REASON_VAR[r.code] }} />
                    <span className="font-mono text-xs font-semibold">{r.code}</span>
                  </div>
                  <div className="mt-1 text-xs text-ink-2">{r.when}</div>
                </td>
                <td className="p-3">{r.attributedTo}</td>
                <td className="p-3">{ACTION_LABEL[r.defaultAction]}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="p-3 border-t border-line text-xs text-ink-2">
          Attribution says whose fault it is. Policy picks the action, and an operator can change it without touching the
          engine. Two guards sit on top: never change more than 20% of the pool at once, and halt automation if half of
          one job&apos;s nodes would change together, because that points at something shared.
        </p>
      </div>
      <pre className="overflow-x-auto rounded-xl border border-line bg-surface p-4 text-[11px] leading-relaxed font-mono">
        {JSON.stringify({ ...example, action: undefined }, null, 2)}
      </pre>
    </div>
  );
}

function Limits() {
  const limits = [
    ["Three traces.", "Thresholds were set by hand on three jobs. The robustness sweep shows they are not on a knife edge, not that they are right."],
    ["History is synthetic.", "Signal types follow what Meta reports for lemon detection. The weights are illustrative. Meta's lemons cause repeated failures; this applies the idea to slowdowns."],
    ["The data may not carry over.", "ByteDance's cluster was dedicated to training with an overprovisioned network. A shared cloud may see more node problems than workload problems."],
    ["Monitoring costs something.", "I did not measure overhead. I treat under 1% as a budget, a target here, not a result."],
    ["The goodput model is simple.", "Assumed restart cost and checkpoint interval. It does not price corrupted training, which is why pulling the chip looks like a cost."],
    ["Not production code.", "It defines behavior and thresholds. It does not operate hardware. GPU error codes and collective-communication details belong with the people who run the fleet."],
  ];
  return (
    <div className="grid gap-6 grid-cols-[minmax(0,1fr)] lg:grid-cols-[1fr_1.4fr]">
      <div className="grid gap-4">
        <div className="rounded-xl border border-line bg-surface p-4">
          <h3 className="font-semibold text-sm">Real</h3>
          <ul className="mt-2 space-y-1.5 text-sm text-ink-2 list-disc pl-4">
            {data.meta.real.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </div>
        <div className="rounded-xl border border-line bg-surface p-4">
          <h3 className="font-semibold text-sm">Synthetic, and labeled everywhere it appears</h3>
          <ul className="mt-2 space-y-1.5 text-sm text-ink-2 list-disc pl-4">
            {data.meta.synthetic.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </div>
      </div>
      <ol className="rounded-xl border border-line bg-surface divide-y divide-[var(--border)]">
        {limits.map(([t, d], i) => (
          <li key={t} className="p-4 text-sm flex gap-3">
            <span className="text-muted tnum">{i + 1}</span>
            <span>
              <strong>{t}</strong> <span className="text-ink-2">{d}</span>
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

function Footer() {
  return (
    <footer className="border-t border-line mt-6">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 py-8 text-sm text-ink-2 flex flex-col sm:flex-row gap-3 sm:justify-between">
        <p>
          Node Verdict {data.meta.version}. Every number on this page is exported from the tested Python engine. The page
          decides nothing.
        </p>
        <p className="flex gap-4">
          <a className="hover:text-ink" href={REPO}>
            Source
          </a>
          <a className="hover:text-ink" href={`${REPO}/blob/main/docs/sources.md`}>
            Sources checked
          </a>
          <a className="hover:text-ink" href="https://github.com/ByteDance-Seed/StragglerAnalysis">
            ByteDance traces
          </a>
        </p>
      </div>
    </footer>
  );
}
