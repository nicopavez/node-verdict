# Node Verdict: One-Pager

## The problem

A large training job runs on many machines in lockstep. If one is slow, the whole job waits. When a job slows down, the operator has to decide whether to replace a node. Today that decision is made with poor information.

Three different problems look the same from the outside:

1. **A slow node.** It still runs, just behind its peers. Replacing it fixes the job.
2. **A corrupting chip.** It passes health checks, runs at normal speed, and returns wrong answers. Replacing it protects every job that would land on it next.
3. **The customer's setup.** The node is fine. The job is slow because of how it was split across pipeline stages or how its data was batched. Replacing hardware fixes nothing.

The third case is the common one. In ByteDance's study of 3,079 large training jobs, worker problems explained most of the slowdown in only 1.7% of straggling jobs. Most of the rest was the job itself.

Getting it wrong is expensive in both directions. Replace a healthy node and you spend a scarce spare and restart the job for nothing. Leave a bad node in place and the job keeps running slow. In a GPU cloud where spares are the constraint, the first mistake is the one that compounds.

## Who feels it

**Fleet operations.** Owns the spare pool and the repair loop. Today they either replace on any slowness, which burns spares on healthy nodes, or wait for a hard fault, which leaves slow and corrupting nodes in service.

**The customer's ML team.** Sees one job slow down and opens a ticket. If the cause is their pipeline split, nobody tells them, and they wait for a hardware fix that will never come.

**Support and account teams.** Field the ticket. Without a clear owner for the slowdown, the conversation goes in circles.

## What I am proposing

A verdict step between health signals and repair. Before anything is replaced, it answers one question: is this slowdown the node or the job?

It uses three pieces of evidence:

1. **Stage peers.** Compare each worker to the other workers doing the same pipeline stage, not to the whole job. A slow stage is the job. A slow worker inside a normal stage is the node.
2. **Cross-job history.** Check whether this node was the outlier in other customers' jobs. Only the cloud has this. One job cannot separate a bad node from a bad position. Several jobs can.
3. **Training anomalies.** A node that keeps producing loss spikes across jobs while passing idle checks is a corruption suspect, even if it is fast.

The output is a node condition with a stable reason code and an owner (node or job). A separate policy turns it into an action: replace at the next checkpoint, quarantine and retest, watch, or tell the customer. Two guards stop automation from running away: never change more than 20% of a pool at once, and halt if many nodes in one job flag together.

The rules are deterministic. No model decides whether hardware gets pulled. Every verdict comes with its evidence and can be tuned by editing one threshold.

## What the proof of concept shows

On a 32-node pool running three real training traces, with four planted problems:

| | Naive repair | Good peer-aware detector | Node Verdict |
|---|---|---|---|
| Healthy nodes replaced | 3 | 0 | 0 |
| Spares used (of 4) | 4 | 1 | 2 |
| Corrupting chip pulled | No | No | Yes |
| Slow jobs given the right owner | 1 of 3 | 1 of 3 | 3 of 3 |

The honest read: a good detector already stops the waste of healthy nodes. What a verdict adds is the chip, and a named owner for every slow job, which is what turns a support ticket into an answer. It does not improve goodput in this model, and I do not claim it does.

## What good looks like

- No healthy node is replaced because of how a customer's job was split.
- A chip that corrupts training is pulled even though it passes every idle check.
- Every slow job gets an owner within one checkpoint interval, and the customer hears it when the owner is them.
- Operators can read why any node was pulled, and change the action without changing the engine.

## What I would do next

Run it in shadow mode next to the existing repair loop for a month. Compare what it would have done with what actually happened, and measure how often its verdicts hold up. Ship nothing that acts on hardware until shadow mode shows it is right. The [PRD](PRD.md) has the requirements, metrics and rollout.
