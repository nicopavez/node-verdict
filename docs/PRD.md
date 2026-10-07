# Node Verdict: PRD

## Summary

Add a verdict step to the GPU cloud's repair loop. When a training job slows down, decide whether the cause is the node or the customer's job before any hardware changes. Publish the answer as a node condition with a stable reason code, and let a separate policy pick the action.

This document defines the behavior. The proof of concept in this repo implements it on real ByteDance traces with synthetic node history. See the [one-pager](one-pager.md) for the problem and [design.md](design.md) for the decision table.

## Goal

Spend spares only on nodes that are actually bad, catch corrupting chips that pass health checks, and tell customers when the slowdown is their setup.

## Non-goals

- Replacing hard-fault repair. Nodes that fail outright already have a working loop (fault code, cordon, drain, replace). This sits next to it.
- Fixing the customer's job. A workload verdict explains the cause. It does not rebalance the pipeline.
- Diagnosing GPU error codes or network fabric faults. Those belong with the fleet and network teams. This consumes their signals.
- A learned model in the decision path. Not until there are labeled repair outcomes to fit it to.

## Users

| User | Needs |
|---|---|
| Fleet operations | Know which flagged nodes to replace, and why, without burning spares on healthy ones |
| Customer ML team | Know whether to wait for a hardware fix or change their job |
| Support | A clear owner for a slowdown ticket |
| Customer automation | A stable reason code to act on |

## Requirements

### Verdict engine

1. Compare each rank to its **stage peers** (same pipeline stage, other data-parallel replicas). Never to the whole job.
2. Apply rules in a fixed order. The first one that fires wins for a node:
   1. `SDCSuspect`: training anomalies in 2+ jobs, idle checks pass, timing normal.
   2. `NodeLemon`: slower than stage peers by 1.15x in 80%+ of steps, and the node was the outlier in 2+ jobs with enough weighted history. `NodeSuspect` if only this job is on record.
   3. `WorkloadImbalance`: the whole stage runs 1.15x+ the job median and the rank matches its peers.
3. A node with no matching rule gets **no condition**. There is no "Healthy" verdict.
4. Every verdict carries its evidence (signal, value, note), an owner (node or job) and an ordinal confidence (low, medium, high).
5. Same inputs, same verdicts. Deterministic.

### Contract

6. Verdicts are Kubernetes-style node conditions under a versioned API.
7. The four reason codes are frozen for v1. A rename or a change in meaning needs a new API version.
8. A workload verdict never changes a node.

### Policy

9. Actions are config, separate from the engine:

| Verdict | Default action |
|---|---|
| `NodeLemon` | Replace at the next checkpoint |
| `SDCSuspect` | Quarantine and retest under realistic load |
| `NodeSuspect` | Watch. No node change |
| `WorkloadImbalance` | Tell the customer. No node change |

10. Fleet cap: never change more than 20% of a pool at once.
11. Correlation guard: if half of one job's nodes would change together, halt automation for that job and page a person.
12. Node changes wait for a checkpoint boundary. No mid-step restarts.

### Non-functional

13. Monitoring overhead under 1% of training throughput. ByteDance reports 0.86% for online corruption detection, so this is achievable but must be measured.
14. Verdict within one checkpoint interval of the slowdown starting.
15. Every threshold is editable config, with a robustness report showing where each one flips a verdict.

## Metrics

Lead with the counts. They do not depend on modeling assumptions.

| Metric | Type | Target for v1 shadow mode |
|---|---|---|
| Healthy nodes that would have been replaced | Primary | Fewer than the current repair loop, measured on the same events |
| Spares spent on nodes later confirmed bad | Primary | Higher share than the current loop |
| Corrupting chips caught before a customer reports them | Primary | Count, with retest confirmation |
| Slow jobs given an owner that later proved right | Primary | Majority, audited by hand on a sample |
| Node verdicts reversed after retest | Guardrail | Low and falling. Each reversal is reviewed |
| Training throughput overhead | Guardrail | Under 1% |
| Times the correlation guard fired | Guardrail | Every firing reviewed |
| Goodput | Secondary | Reported, never the headline. In the proof of concept, almost all goodput gain comes from checkpoint timing and peer comparison, which a good detector already does |

## Rollout

1. **Shadow.** Run next to the existing repair loop. Act on nothing. Log what it would have done. Compare weekly against what operations actually did and what retests found.
2. **Advisory.** Show verdicts to operators and support in their tools. A person still makes every hardware change. Start telling customers about `WorkloadImbalance` verdicts, with the evidence.
3. **Automatic, narrow.** Automate `NodeLemon` replacement only, behind the fleet cap and the correlation guard, and only for customers who opt in. `SDCSuspect` stays human-approved until the retest process is proven.
4. **Customer API.** Publish the node conditions so customers can automate on them.

Each step needs the previous step's guardrail metrics to hold for a full month.

## Acceptance criteria for the proof of concept

- [x] On the demo pool, the planted bad node is `NodeLemon`, the planted chip is `SDCSuspect`, and no healthy node gets a node verdict.
- [x] Without cross-job history, the bad node drops to `NodeSuspect` and the chip gets no verdict.
- [x] The simulator includes a peer-aware baseline, and the docs state what attribution adds beyond it.
- [x] No threshold setting in the robustness sweep replaces or pulls a healthy node.
- [x] Reason codes are pinned by a test.
- [x] The web demo renders exported data and decides nothing. A test fails if the export drifts.

## Risks and open questions

1. **Thresholds are set on three traces.** The robustness sweep says they are not on a knife edge. It does not say they are right. Shadow mode on real fleet data is the real test.
2. **The data may not carry over.** ByteDance ran a dedicated cluster with an overprovisioned network. A shared cloud may see more node and network problems, which would change the mix of verdicts.
3. **Position versus node.** A rank can be slow because of where it sits (a congested link, a hot rack) rather than the node itself. Cross-job history is the defense. How much history is enough is an open question.
4. **Retest design.** What "retest under realistic load" means for a suspected corrupting chip, and how long it takes, is not defined yet. It needs the fleet team.
5. **Telling customers.** A `WorkloadImbalance` message has to be specific enough to act on and careful enough not to sound like blame. That needs support and the customer's ML team in the loop.
6. **Overhead.** Per-rank step timing has a cost. AWS found its own health agent caused periodic slowdowns in a training job. The 1% budget has to be measured, not assumed.
