# Source check

Every number and product claim in the README, checked against its source on 2026-10-06. Quotes are verbatim. Where the README said something the source does not support, the last column says what changed.

## Numbers

| Claim in the README | Source | What the source says | Status |
|---|---|---|---|
| 3,079 jobs studied | ByteDance, OSDI 2025, section 3.1 | "This produces 3079 jobs for our analysis." Jobs use at least 128 GPUs, January to May 2024. | Correct. Added the 128 GPU floor. |
| 42.5% of jobs straggled | Same, section 4.1 | "42.5% of the jobs are at least 10% slower due to stragglers." | Correct. Reworded to "at least 10% slower" to match the definition. |
| 10.4% of GPU hours wasted | Same, section 4.1 | "Across all our traces we found that 10.4% of the allocated GPU hours are wasted due to stragglers." | Correct. |
| Worker problems explain most of the slowdown in 1.7% of straggling jobs | Same, section 5.1 | "worker problems contribute to more than 50% of the observed slowdown for only 1.7% of straggling jobs." | Correct. Added that the cluster already ran health checks, so this is what is left after them. |
| 3.04x vs 1.28x | Same, section 5.1 | "slowdown for jobs with problematic workers is 3.04 compared to the average slowdown of 1.28." | Correct. |
| Most causes were in the job | Same, sections 5.2 and 5.3 | Stage partitioning imbalance "was a common cause of stragglers." Sequence length imbalance is the next cause analyzed. | Correct. |
| The cluster is dedicated, with ample network capacity | Same, section 3.1 | "dedicated for training and shared internally by multiple teams." "The network is overprovisioned and carefully tuned." | Correct. |
| Meta's lemon detector: more than 85% accuracy | Meta, "Revisiting Reliability", section IV-A | "successfully identify 40 faulty nodes ... achieving more than 85% accuracy." | Correct. |
| Large-job failures (512+ GPUs) from 14% to 4% | Same | "led to 10% reduction in large job failures (512+ GPUs), from 14% to 4%." | Correct. |
| Lemon signals: excluded jobs, repair tickets, multi-node failures | Same | Lists `excl_jobid_count`, `xid_cnt`, `tickets`, `out_count`, `multi_node_node_fails`, `single_node_node_fails`, `single_node_node_failure_rate`. | Correct, and a subset. Added two caveats: Meta's lemons cause repeated job failures, not slowdowns, and Meta found exclusions alone "did not have a strong correlation with node failures." |
| Synthetic benchmarks miss over 60% of defective GPUs | ByteDance, "SDCs in the Wild", OSDI 2026 | Standard practice relies on synthetic microbenchmarks, which "miss over 60% of defective devices." | Correct. |
| 0.86% overhead for online corruption detection | ByteDance, AEGIS, OSDI 2026 | "13 faulty GPUs while incurring only 0.86% performance overhead" over 35 million GPU hours. | Correct. |
| AWS found its own health agent slowed training jobs | AWS EKS team, The New Stack (sponsored) | A customer running NCCL training "found that NMA itself was causing periodic slowdowns." | Correct. |
| A 20% fleet cap on repairs | AWS EKS docs and AWS containers blog | "Karpenter will not terminate more than one-fifth of a NodePool at once." Auto repair is disabled by default when "More than 20% of the nodes in the NodePool are unhealthy." | Correct. Now cited to AWS directly. |

Three quotes I added because they support the design directly:

- Meta: "Historic data is necessary to find defective nodes." This is the case for cross-job history.
- Meta: their lemon thresholds "were tuned manually based on accuracy and false positive rate." A fleet operator at scale chose hand-set rules too.
- AWS: EKS auto repair does not act on pressure conditions because they "often indicate issues with application behavior, workload configuration, or resource limits rather than node-level failures, making it difficult to determine an appropriate default repair action." That is the node-or-job question, named by the people who run auto repair.

## Products and research

| Claim in the README | What the source says | Status |
|---|---|---|
| CoreWeave Straggler Detection is in preview | Installed and enabled by default in SUNK v8.0.0 and later. It names the rank, node and pod, and the operator drains and requeues. | **Fixed.** No longer called a preview. |
| A person still decides at CoreWeave whether the cause is the node, the network, or the code | The docs surface telemetry for investigation. They do not claim to separate node, network and code causes. | Correct. |
| Crusoe AutoClusters replaces nodes on critical failures for workloads that opt in | The add-on is enabled per cluster. "All remediation actions default to OFF" and are turned on per issue type. Otherwise it "detects failures and sends notifications." | **Fixed.** Now says remediation is off by default and enabled per issue type. |
| AWS EKS and NVSentinel replace nodes that fail outright | EKS replaces or reboots on hardware, kernel, network and storage conditions. NVSentinel detects, cordons, drains and remediates GPU faults (ECC, XID, thermal). Neither page covers slow nodes. | Correct. |
| Research (GREYHOUND, Guard, SysOM-AI) detects slow GPUs and links | GREYHOUND detects slow GPUs and links and mitigates them. Guard combines online monitoring with an offline node sweep. SysOM-AI diagnoses root cause across layers and runs on 80,000+ GPUs at Alibaba. | **Fixed.** "Published as research, no product built on them" was too strong for SysOM-AI, which runs in production. Now says they run inside one operator's fleet. |

## Removed

Three sources were listed but no claim in the README cites them: the Llama 3 paper, the Alibaba training survey, and the SemiAnalysis ClusterMAX review. I removed them rather than leave uncited entries.
