#!/usr/bin/env python3
"""
liveness.py — apply RRSI's noise-adjusted floor to the fleet's OWN durable recipes.

WHY THIS EXISTS
The fleet celebrates recipes for surviving 30+ wipes. RRSI names that as a failure mode
called NOISE CHASING: a recipe is credited for surviving while the thing it guarded drifts
underneath it. Durability is absence of measurement, not evidence of value.

So: measure. For each recipe, three numbers.
  SPREAD    variance of its output across recent runs. A recipe whose output does not vary
            is either deterministic (fine, say so) or being read by nothing.
  COST      what it costs to run. RRSI's cost rule: extra tokens must be paid for by
            measured gain. No fleet recipe has ever accounted for this.
  CONSUMERS what actually reads its output. A recipe nothing consumes is dead weight that
            happens to still run.

The floor: a recipe earns its place only if its gain clears the variance measured on an
UNCHANGED baseline. The fleet has no baseline. That absence is the finding.
"""
import json, os, sys, re, subprocess, statistics
from collections import defaultdict

TODAY = "2026-09-30"

# The fleet's own durable recipes, as claimed in the agent's own memory.
RECIPES = [
  dict(name="JEV probe bootstrap",
       what="git clone SuperInstance/jev-quilt, cp 2 files, run",
       claimed_wipes=40, cost_tokens="~0 (local)",
       artifact="/tmp/jev_probe/run/jev_hourly_report.md",
       consumers=["analyst reading the report by hand"],
       variance_measured=False),
  dict(name="Taps recipe v5",
       what="kill at 75s, hand-write the fallback piece",
       claimed_wipes=14, cost_tokens="0 (the fallback is written by hand)",
       artifact="/tmp/superinstance-advisor/sessions/taps-fallback-*.md",
       consumers=["none found — the canon API cell is the real artifact"],
       variance_measured=False),
  dict(name="NAS Avail=0 mirror to /tmp",
       what="write to /tmp when the NAS quota is full",
       claimed_wipes=23, cost_tokens="0",
       artifact="/tmp/...",
       consumers=["this agent"],
       variance_measured=False),
  dict(name="subject-named JEV batching",
       what="name the subject in the question or the whole state answers",
       claimed_wipes=11, cost_tokens="low",
       artifact="n/a (a method)",
       consumers=["the JEV probe"],
       variance_measured=False),
  dict(name="FNV-1a hand-roll in Python 3.12",
       what="hashlib has no FNV-1a 64; write it",
       claimed_wipes=1, cost_tokens="0",
       artifact="n/a (a fact)",
       consumers=["every canary in the fleet"],
       variance_measured=False),
]

def report():
    print("  %-34s %6s %7s %-11s %s" % ("recipe", "wipes", "cost", "variance", "consumers"))
    print("  " + "-"*96)
    for r in RECIPES:
        var = "NOT MEASURED" if not r["variance_measured"] else "measured"
        flag = ""
        if r["consumers"] and r["consumers"][0].startswith("none"):
            flag = "   <-- nothing consumes this"
        print("  %-34s %6d %7s %-11s %s%s" % (r["name"][:34], r["claimed_wipes"],
              r["cost_tokens"], var, ", ".join(r["consumers"])[:28], flag))
    print()
    unmeasured = sum(1 for r in RECIPES if not r["variance_measured"])
    print("  %d of %d recipes have ANY measured variance." % (unmeasured, len(RECIPES)))
    print("  RRSI's floor cannot be applied to a recipe with no baseline to measure against.")
    print()

if __name__ == "__main__":
    if "--json" in sys.argv:
        json.dump({"date": TODAY, "recipes": RECIPES}, open("liveness.json","w"), indent=1)
        print("  wrote liveness.json")
    else:
        report()
