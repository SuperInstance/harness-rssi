# Four things Casey sent, and the one thing they say about us

Read on 2026-09-30. Fetched and summarised from primary sources: the HuggingFace paper page,
the MarkTechPost write-up of the Google Research release, the MQL5 article, and the pooled
repository's own README. Every claim below with a number attached to it is from the source,
not from me.

---

## 1 · QwenGyre — elastic RL for xLong-horizon agents

*Paper 2609.33848.* Training agents on extreme-long-horizon tasks with online RL. Two
components: an **elastic GPU reallocator** that moves GPUs between rollout and training
without interrupting live executions, and a **trajectory processor** that reconstructs
branching histories, scores partial progress, and **deduplicates redundant paths**.

Result: Qwen~3.8 2.4B-param class, 700K tokens per rollout, **52.5% → 58.5% on
NL2RepoBench in 48 steps**; 1.85× and 1.78× over Colocate and Async baselines.

**The part that is us.** The trajectory processor's job is bounding the cost of an agent
that explores a branching space by not paying twice for branches it has already seen. That
is *exactly* what the fleet does wrong, and it is why the 141-Rust-crate pass needed four
resumable launches, and why recipes get rebuilt from memory after a wipe. **We have a
trajectory problem and no trajectory processor.**

Note also the elastic reallocator's premise: long rollouts have severe variance, so a
static GPU split idles. Our agent allocation is entirely static and hand-tuned per model.
That is the same problem, one layer down, and it is why Groq's cheap tier matters and why
the expensive tiers sit idle.

## 2 · RRSI — agents that improve their own harness, and this one is a critique of us

*Google Cloud AI Research with UNC-Chapel Hill, Stanford, WashU.* An agent rewrites its own
harness — prompts, tools, memory, control flow, sub-agents — **without touching weights.**

It identifies three failure modes of self-improving harnesses, and all three are live here:

| failure mode | where it already is in this fleet |
|---|---|
| **benchmark-specific fitting** | recipes written to survive *this* sandbox's exact failure shape, then frozen |
| **noise chasing** | a "30-wipe-durable" recipe credited for surviving while the thing it guarded drifted underneath it |
| **complexity accumulation** | every wipe adds a branch, a special case, a `NEW VARIANT` — the fixups compound |

The four regularizers are the interesting part, because two of them are instruments the
fleet does not have:

- **leakage critic** — rejects task names, entities, answers, or benchmark-specific logic
  *before* any scoring. This is the thing that would have caught **every** subagent
  hallucination this session. A subagent that writes "0 READMEs written" is leaking the
  benchmark into the answer.
- **noise-adjusted floor** — a gain must clear the **variance measured on the unchanged
  base harness**. We have no such measurement. Durability has been our proxy for value, and
  **durability is absence of measurement, not evidence of it.**
- **cost rule** — extra inference tokens must be paid for by measured gain. Our recipes
  never account for their own token cost.
- **pruning** — components that stop earning are deletion targets. **We have never pruned a
  recipe.** Not once, across 40+ wipes.

**The uncomfortable part, stated plainly:** I checked the fleet's most-cited durable
artifact tonight. `jev_continuous_probe.py` is 278 lines with **no regression guard and no
known-answer test**. It is the load-bearing recipe of dozens of wipes, and nothing measures
whether it is still earning its keep. It is frozen, not learned.

RRSI's *evidence-aware credit* — log every candidate with its component, hypothesis, diff,
score change, and cost change, so falsified ideas are not retried — is **the witness log
applied to harness changes**. We built the witness chain for cells and never applied it to
recipes. That is the actual gap, and it is bigger than the polyformalism one.

## 3 · pooled — peer-to-peer inference, and the property is privacy not speed

*Nehanth/pooled*, 541★, MIT, JavaScript, WebGPU + WebRTC. One open model across every device
in a room: each device holds a slice of the layers and runs them on its own GPU with its own
WGSL kernels. A 10 KB hidden state crosses a direct WebRTC connection per token — 4 KB on
the MoE. The host samples the next token and drafts ahead speculatively. Qwen 3.8 27B across
~17 GB of pooled memory; 3.6 35B MoE across ~22.5 GB.

**"There is nothing to install and no account, and no server does any of the thinking."**

That sentence is the synergy. The fleet's `no-deletion` doctrine is about *lifetime* — what
survives. Pooled is about *custody* — where it never goes. The pair together is a complete
position on data, and only the custody half is missing.

It also lands squarely on `federated-tinyml-vessel` (F170: 1.3 KB head, FedAvg, learns
without shipping data) and `hwscan`. **F170 trains a small model at the edge; pooled runs a
large one across edges. Same doctrine, two halves, and they compose.** And the WGSL kernels
are the same target Futhark compiles to, so the Futhark lab and pooled are the same
hardware problem wearing two language hats.

## 4 · ASSA — a swarm where a finding is a signal that expires in one tick

*MQL5 article.* A metaheuristic with a **Bulletin Board** (global best), per-agent personal
bests, and three mutually exclusive movement rules: move toward the last agent that found
an improvement (probability `Pc`), or construct a probe attracted to both the personal and
global best, or move randomly. **The call signal persists for exactly one iteration.**

It scored 33.42% and does not qualify for top rankings, because fixed `Pc` and a
one-iteration signal cause premature convergence. The article is honest about its own
failure mode, which is the most interesting part.

**The one-iteration signal is a striking near-miss.** That is a witness with a TTL: "something
improved here, and only next tick." The fleet's witness chain is the opposite — permanent
and unbounded — and that difference is the whole design choice. ASSA chose the short signal
because long ones are noise. The fleet chose the long one because history is the point
(`no deletion`). **Both are right about different things, and the fleet's own
`si-knowledge-graph` recursion has to live with the question of which a given fact is.**

---

## The synthesis

All four are the same shape: **propagating a scarce thing without paying twice and without
freezing.**

| | scarce thing | mechanism for not paying twice | mechanism against freezing |
|---|---|---|---|
| QwenGyre | GPU time | trajectory dedup | elastic reallocation |
| RRSI | harness edits | evidence-aware credit | annealed budget + pruning |
| pooled | model capacity | layer partitioning | device-agnostic protocol |
| ASSA | improvement signals | one-iteration call | (explicitly fails here) |
| **the fleet** | **witness log** | **the chain** | **...none** |

**The fleet is the only one of the five with no anti-freezing mechanism.** We built the
right structure for the wrong failure mode. Our chain is excellent at *not losing* history
and has nothing at all for *not keeping history that stopped earning*.

That is the one actionable thing out of four links, and it is not about Forge, or Futhark,
or P2P inference. It is: **start measuring the recipes.** Apply RRSI's noise-adjusted floor
and pruning to the durable-recipe list, and be prepared to find that the most-cited recipe
in the fleet is earning nothing and nobody can currently tell.

## What I would build next, in order

1. **A recipe liveness instrument.** For each durable recipe: variance of its output across
   recent runs, tokens spent, and whether its output is still *read by anything*. RRSI's
   floor, applied to ourselves. This is the gap the fleet actually has.
2. **Evidence-aware credit for harness changes.** Every recipe edit logged with component,
   hypothesis, diff, and measured effect — the witness chain, applied to recipes instead of
   cells.
3. **A leakage critic on subagent output.** Cheap, and it would have caught four
   subagent failures tonight that all reported success.
4. Then, and only then, the pooled/F170 composition — because it is the most exciting and
   the least urgent.

---

## What the liveness probe found when pointed at the fleet itself

`liveness.py` applies RRSI's three regularizers to the fleet's own durable recipes:

```
  recipe                              wipes    cost   variance     consumers
  JEV probe bootstrap                    40  ~0      NOT MEASURED  analyst reading the report
  Taps recipe v5                         14  0       NOT MEASURED  none found
  NAS Avail=0 mirror to /tmp             23  0       NOT MEASURED  this agent
  subject-named JEV batching             11  low     NOT MEASURED  the JEV probe
  FNV-1a hand-roll in Python 3.12         1  0       NOT MEASURED  every canary

  0 of 5 have ANY measured variance.
```

**Zero.** Not one of the fleet's durable recipes has a measured output distribution, so
RRSI's noise-adjusted floor cannot be applied to any of them. That is the finding, and it
is the same shape as tonight's other eight: **an instrument that cannot tell whether it is
still earning its keep.**

**And the probe immediately caught a bookkeeping error in my own memory.** It listed Taps
recipe v5 as producing `sessions/taps-fallback-*.md` with no consumer. The real artifact is
the **canon cell** the piece is submitted to; the markdown is a local mirror. So the recipe
table — the thing I have been treating as durable record — **had the wrong output
recorded for the recipe that took 14 iterations.** A durable record that cannot say what it
produces is a superstition with good documentation.

**A second measurement, and it is not flattering.** `jev_continuous_probe.py` — the
load-bearing recipe of dozens of wipes, 278 lines — has **no regression guard and no
known-answer test**. It is frozen, not learned. Forty wipes of durability and nothing
measures whether it still works, because nothing ever compared it to a baseline that could
change.

## The two things to do about it

1. **Add a known-answer control to the JEV probe.** It is the single most-cited artifact in
   the fleet's memory and it has no test that would fail if the thing it measures silently
   stopped being the thing it measures. That is the cheapest high-value change on this list.
2. **Start pruning.** RRSI's pruning rule — components that stop producing gains become
   deletion targets — has never once been applied in this fleet. Not to a recipe, not to a
   branch, not to a memory entry. Every wipe *adds*. The archive grows monotonically and
   nothing in the system is capable of saying "this is finished."

The second one is uncomfortable to write down, which is probably why it has not been
written down.
