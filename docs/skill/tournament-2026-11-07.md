# Skill variant tournament, round 1 (2026-11-07)

> **Scope correction (2026-11-07).** This round measures only the skill's **writing
> behaviour**: whether the agent that edits code leaves the right comments, measured
> on comment text. It does **not** measure the product goal, which is whether those
> comments help a *later*, possibly weaker, agent make correct changes. Earlier text
> described the Haiku arms as "the less capable model the hypothesis is about". That
> was wrong: Haiku was the *writer* here, and the hypothesis is about weaker
> *readers*. Read every result below as "how good a comment writer is model X with
> variant Y", not as evidence about the product hypothesis. The primary test is now
> the downstream sequence eval (#19). `comment-edit` is a guardrail.

Tracked in #26. Design and winner rule: [design.md](design.md). The user approved
this run after a $0.57 pilot.

## Setup

- **Arms:** `control` (no skill), `lean`, `principled`, `procedural`, `examples` and
  `newcomer` (see `skill-variants/variants.json`).
- **Eval:** `comment-edit`, 20 synthetic cases, 5 per family. Case set `44251a9bf333`
  as run; `fefe9c3ee9fc` after the fixes below. Split seed 7: 12 train, 8 test.
- **Runs:** 3 reps per case and arm, on `claude-sonnet-5-5` and `claude-haiku-5-5`
  separately, giving **720 attempts with 0 harness errors**. Measured spend was
  **$13.60** (API-equivalent figures reported by Claude Code; the projection was
  $12-14).
- **Harness:** Claude Code 2.1.319 headless with `--restricted` (file tools only, no
  shell, user plugins off). The variant is loaded as a session plugin and invoked
  explicitly. The user's global CLAUDE.md may load, identically in every arm.
- **Analysis:** `python -m evaluation.skill_eval.compare <flow> --split <split>`. Each
  arm is compared with the control on the same cases, with 95% intervals over cases
  (1.96 x sd / sqrt(n)).

## Post-hoc grader fixes (disclosed)

Reading the failing transcripts showed that 3 of the 4 cases on which nearly every
arm failed were grader or case errors. They were fixed after the results were seen,
and every row was **regraded offline** from the diffs in its trace
(`python -m evaluation.skill_eval.regrade`). A round-trip regrade with the
unchanged grader reproduced all 378 earlier grades exactly. Raw flows are kept
unmodified, and both sets of numbers are below.

1. **Markup.** Backticks and asterisks are now removed before anchor matching.
   ``Returns the units of ``sku`` left in ``stock`` `` was wrongly scored as missing a
   fact, in all 18 attempts on `maintain-reserve-contract`. Neutral between arms.
2. **`maintain-username-unicode`.** The casefold rationale was verbatim-protected
   text, but the requested change legitimately rewrites it (NFKC plus casefold). It
   is now a required fact that may be reworded. Found in the control's output, and
   neutral.
3. **`capture-stay-checkout-exclusive`.** The noise budget rose from 3 to 6, so a
   caller-contract docstring for the new public function (core principle P-22) fits.
   **This fix favours the skill arms**, because the control wrote no docstring.

Not fixed in this round, and recorded for the next case revision (#21):
`audit-cache-ttl` requires the literal value ("300" / "five minutes"). P-27 tells
agents to point to the constant instead, and some skill arms did exactly that
("expire `TTL_SECONDS` after they are stored").

## Result: a null tournament

Under the design's rule (screen on **train**; keep only arms above the control
beyond noise, with no guardrail regression), **no arm qualifies on either model.**

| Model | Train, regraded: Δpass vs control | Reading |
| --- | --- | --- |
| Sonnet 5.5 | +0.06 to +0.08 for every arm; every interval crosses 0 | No detectable effect. The control is already at 0.83 on train, so headroom is small |
| Haiku 5.5 | −0.11 to −0.22 for every arm; `newcomer` −0.22 ± 0.20 (wholly below 0) | The skills hurt on train, through the audit family. Test leans the other way (+0.00 to +0.13) with wide intervals |

Train and test disagree in direction on Haiku. With 12 and 8 cases, single cases
move the means by about 8 points, which is the noise floor that #21 exists to
lower.

## What the per-family view shows (Haiku, all cases, regraded)

| Family | control | lean | principled | procedural | examples | newcomer |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| capture | 0.60 | **0.93** | 0.73 | 0.73 | 0.73 | 0.80 |
| audit | **0.80** | 0.53 | 0.73 | 0.47 | 0.67 | 0.47 |
| maintain | **1.00** | 0.87 | 0.87 | 0.80 | 0.73 | 0.93 |
| restrain | 1.00 | 1.00 | 1.00 | 0.93 | 1.00 | 0.87 |

Every skill raises **capture**, which is its purpose, and lowers **audit** and
**maintain** on the weaker model. The audit failures come mostly from **rewriting
still-valid comments** (`preserved` fails 4-5 of 15 in lean, procedural and
newcomer, against 0 for the control) and adding lines during comment-only requests.
For example, Haiku replaced an accurate clock comment with incident narration. That
breaks P-13 ("leave valid comments word for word") and P-29 ("describe the design,
not its history"). A weaker model over-applies "capture the reasons you find". On
Sonnet the effect is smaller and mixed: audit runs from 0.73 (`principled`) to
1.00 (`examples`), against 0.87 for the control, and capture still rises with
`lean` (0.93 against 0.60). The longest, most capture-oriented
variants (`newcomer`, `procedural`) show it most.

## Hypotheses (design.md), round 1 verdicts

| Variant | Hypothesis | Verdict |
| --- | --- | --- |
| `lean` | Matches `principled` at fewer tokens | **Consistent:** not distinguishable from `principled` on either model, and the cheapest. Highest capture rate on both models (directional) |
| `principled` | Beats control on pass, especially maintain/audit | **Not supported** (null on Sonnet; below control on Haiku train) |
| `procedural` | Diff scan raises maintain/audit | **Refuted directionally:** the lowest audit rate on Haiku, and more noise |
| `examples` | Lower restrain noise, higher capture | **Inconclusive:** restrain is at the ceiling for every arm |
| `newcomer` | Higher capture recall, more restrain failures | **Partly supported:** capture up, restrain down on Haiku; worst overall on Haiku train |

## Limits

- 20 synthetic cases authored in this repository. The intervals are wide, and these
  are proxy scores, not downstream benefit (#19).
- One harness (Claude Code), no shell for the agent, and one run date.
- Post-hoc grader fixes are disclosed above. Raw results tell the same story: no arm
  beats the control on train for either model.

## What follows from this round (revised after the scope correction)

- **No climb on this proxy.** Its noise budget presumes that leaner is better, so
  climbing it could optimise *away* from what helps weaker readers. That can only be
  measured downstream.
- **Keep the finding as a writer guardrail.** A weaker *writer* with these skills
  rewrites still-valid comments during comment-only requests. Any variant carried
  into the downstream eval must not regress `preserved` or `bad_claims` here.
- **Next:** the downstream sequence eval (#19), which compares skill-maintained inline
  comments with an AI-maintained docs folder (the user's current practice) and with no
  added context, as measured by a weaker reader's follow-up changes.

## Tables (generated by `evaluation.skill_eval.compare`)

Local reports (traces are gitignored): `.claude/hillclimb/comment-edit-{sonnet,haiku}{,-regraded}/report.html`.

#### comment-edit-sonnet — split: train

| arm | pass | Δpass vs control (95% CI) | Δbehavior | Δbad_claims | Δnoise_lines | cost/attempt | errors |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| control | 0.750 | — | — | — | — | $0.0224 | 0 |
| lean | 0.750 | -0.000 ± 0.161 (n=12) | +0.00 | +0.00 | +0.22 | $0.0286 | 0 |
| principled | 0.722 | -0.028 ± 0.054 (n=12) | +0.00 | +0.00 | +0.44 | $0.0375 | 0 |
| procedural | 0.750 | +0.000 ± 0.000 (n=12) | +0.00 | +0.00 | +0.36 | $0.0421 | 0 |
| examples | 0.750 | +0.000 ± 0.000 (n=12) | +0.00 | +0.00 | +0.36 | $0.0372 | 0 |
| newcomer | 0.750 | +0.000 ± 0.000 (n=12) | +0.00 | +0.00 | +0.67 | $0.0419 | 0 |

Pass rate by family (mean over cases of the per-case rep average):

| arm | audit | capture | maintain | restrain |
| --- | ---: | ---: | ---: | ---: |
| control | 1.00 | 0.67 | 0.33 | 1.00 |
| lean | 0.78 | 0.89 | 0.33 | 1.00 |
| principled | 0.89 | 0.67 | 0.33 | 1.00 |
| procedural | 1.00 | 0.67 | 0.33 | 1.00 |
| examples | 1.00 | 0.67 | 0.33 | 1.00 |
| newcomer | 1.00 | 0.67 | 0.33 | 1.00 |

#### comment-edit-sonnet — split: all

| arm | pass | Δpass vs control (95% CI) | Δbehavior | Δbad_claims | Δnoise_lines | cost/attempt | errors |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| control | 0.767 | — | — | — | — | $0.0224 | 0 |
| lean | 0.817 | +0.050 ± 0.144 (n=20) | +0.00 | +0.00 | +0.35 | $0.0286 | 0 |
| principled | 0.733 | -0.033 ± 0.164 (n=20) | +0.00 | +0.00 | +0.65 | $0.0374 | 0 |
| procedural | 0.750 | -0.017 ± 0.146 (n=20) | +0.00 | +0.00 | +0.63 | $0.0420 | 0 |
| examples | 0.800 | +0.033 ± 0.156 (n=20) | +0.00 | +0.00 | +0.47 | $0.0372 | 0 |
| newcomer | 0.750 | -0.017 ± 0.186 (n=20) | +0.00 | +0.00 | +0.85 | $0.0418 | 0 |

Pass rate by family (mean over cases of the per-case rep average):

| arm | audit | capture | maintain | restrain |
| --- | ---: | ---: | ---: | ---: |
| control | 0.87 | 0.60 | 0.60 | 1.00 |
| lean | 0.80 | 0.87 | 0.60 | 1.00 |
| principled | 0.73 | 0.60 | 0.60 | 1.00 |
| procedural | 0.80 | 0.60 | 0.60 | 1.00 |
| examples | 1.00 | 0.60 | 0.60 | 1.00 |
| newcomer | 0.80 | 0.60 | 0.60 | 1.00 |

#### comment-edit-sonnet-regraded — split: train

| arm | pass | Δpass vs control (95% CI) | Δbehavior | Δbad_claims | Δnoise_lines | cost/attempt | errors |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| control | 0.833 | — | — | — | — | $0.0224 | 0 |
| lean | 0.889 | +0.056 ± 0.194 (n=12) | +0.00 | +0.00 | +0.22 | $0.0286 | 0 |
| principled | 0.889 | +0.056 ± 0.177 (n=12) | +0.00 | +0.00 | +0.39 | $0.0375 | 0 |
| procedural | 0.917 | +0.083 ± 0.163 (n=12) | +0.00 | +0.00 | +0.36 | $0.0421 | 0 |
| examples | 0.917 | +0.083 ± 0.163 (n=12) | +0.00 | +0.00 | +0.33 | $0.0372 | 0 |
| newcomer | 0.889 | +0.056 ± 0.109 (n=12) | +0.00 | +0.00 | +0.56 | $0.0419 | 0 |

Pass rate by family (mean over cases of the per-case rep average):

| arm | audit | capture | maintain | restrain |
| --- | ---: | ---: | ---: | ---: |
| control | 1.00 | 0.67 | 0.67 | 1.00 |
| lean | 0.78 | 0.89 | 0.89 | 1.00 |
| principled | 0.89 | 0.67 | 1.00 | 1.00 |
| procedural | 1.00 | 0.67 | 1.00 | 1.00 |
| examples | 1.00 | 0.67 | 1.00 | 1.00 |
| newcomer | 1.00 | 0.67 | 0.89 | 1.00 |

#### comment-edit-sonnet-regraded — split: all

| arm | pass | Δpass vs control (95% CI) | Δbehavior | Δbad_claims | Δnoise_lines | cost/attempt | errors |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| control | 0.817 | — | — | — | — | $0.0224 | 0 |
| lean | 0.917 | +0.100 ± 0.151 (n=20) | +0.00 | +0.00 | +0.35 | $0.0286 | 0 |
| principled | 0.850 | +0.033 ± 0.177 (n=20) | +0.00 | +0.00 | +0.62 | $0.0374 | 0 |
| procedural | 0.867 | +0.050 ± 0.159 (n=20) | +0.00 | +0.00 | +0.63 | $0.0420 | 0 |
| examples | 0.933 | +0.117 ± 0.152 (n=20) | +0.00 | +0.00 | +0.45 | $0.0372 | 0 |
| newcomer | 0.833 | +0.017 ± 0.198 (n=20) | +0.00 | +0.00 | +0.78 | $0.0418 | 0 |

Pass rate by family (mean over cases of the per-case rep average):

| arm | audit | capture | maintain | restrain |
| --- | ---: | ---: | ---: | ---: |
| control | 0.87 | 0.60 | 0.80 | 1.00 |
| lean | 0.80 | 0.93 | 0.93 | 1.00 |
| principled | 0.73 | 0.67 | 1.00 | 1.00 |
| procedural | 0.80 | 0.67 | 1.00 | 1.00 |
| examples | 1.00 | 0.73 | 1.00 | 1.00 |
| newcomer | 0.80 | 0.60 | 0.93 | 1.00 |

#### comment-edit-haiku — split: train

| arm | pass | Δpass vs control (95% CI) | Δbehavior | Δbad_claims | Δnoise_lines | cost/attempt | errors |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| control | 0.833 | — | — | — | — | $0.0019 | 0 |
| lean | 0.722 | -0.111 ± 0.246 (n=12) | +0.00 | +0.00 | -0.08 | $0.0024 | 0 |
| principled | 0.694 | -0.139 ± 0.170 (n=12) | +0.00 | +0.00 | +0.58 | $0.0030 | 0 |
| procedural | 0.583 | -0.250 ± 0.280 (n=12) | +0.00 | +0.00 | +0.67 | $0.0035 | 0 |
| examples | 0.667 | -0.167 ± 0.234 (n=12) | +0.00 | +0.00 | +0.25 | $0.0031 | 0 |
| newcomer | 0.556 | -0.278 ± 0.210 (n=12) | +0.00 | +0.00 | +0.75 | $0.0033 | 0 |

Pass rate by family (mean over cases of the per-case rep average):

| arm | audit | capture | maintain | restrain |
| --- | ---: | ---: | ---: | ---: |
| control | 1.00 | 0.67 | 0.67 | 1.00 |
| lean | 0.56 | 0.89 | 0.44 | 1.00 |
| principled | 0.67 | 0.67 | 0.44 | 1.00 |
| procedural | 0.33 | 0.67 | 0.44 | 0.89 |
| examples | 0.67 | 0.78 | 0.22 | 1.00 |
| newcomer | 0.44 | 0.67 | 0.33 | 0.78 |

#### comment-edit-haiku — split: all

| arm | pass | Δpass vs control (95% CI) | Δbehavior | Δbad_claims | Δnoise_lines | cost/attempt | errors |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| control | 0.800 | — | — | — | — | $0.0019 | 0 |
| lean | 0.783 | -0.017 ± 0.180 (n=20) | +0.00 | +0.02 | -0.42 | $0.0024 | 0 |
| principled | 0.750 | -0.050 ± 0.179 (n=20) | +0.00 | +0.00 | +0.03 | $0.0030 | 0 |
| procedural | 0.633 | -0.167 ± 0.235 (n=20) | +0.00 | +0.00 | +0.20 | $0.0034 | 0 |
| examples | 0.700 | -0.100 ± 0.202 (n=20) | +0.00 | +0.00 | +0.02 | $0.0031 | 0 |
| newcomer | 0.633 | -0.167 ± 0.198 (n=20) | +0.00 | +0.00 | +0.38 | $0.0033 | 0 |

Pass rate by family (mean over cases of the per-case rep average):

| arm | audit | capture | maintain | restrain |
| --- | ---: | ---: | ---: | ---: |
| control | 0.80 | 0.60 | 0.80 | 1.00 |
| lean | 0.53 | 0.93 | 0.67 | 1.00 |
| principled | 0.73 | 0.67 | 0.60 | 1.00 |
| procedural | 0.47 | 0.60 | 0.53 | 0.93 |
| examples | 0.67 | 0.73 | 0.40 | 1.00 |
| newcomer | 0.47 | 0.60 | 0.60 | 0.87 |

#### comment-edit-haiku-regraded — split: train

| arm | pass | Δpass vs control (95% CI) | Δbehavior | Δbad_claims | Δnoise_lines | cost/attempt | errors |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| control | 0.917 | — | — | — | — | $0.0019 | 0 |
| lean | 0.806 | -0.111 ± 0.218 (n=12) | +0.00 | +0.00 | -0.08 | $0.0024 | 0 |
| principled | 0.806 | -0.111 ± 0.123 (n=12) | +0.00 | +0.00 | +0.58 | $0.0030 | 0 |
| procedural | 0.694 | -0.222 ± 0.232 (n=12) | +0.00 | +0.00 | +0.67 | $0.0035 | 0 |
| examples | 0.806 | -0.111 ± 0.186 (n=12) | +0.00 | +0.00 | +0.25 | $0.0031 | 0 |
| newcomer | 0.694 | -0.222 ± 0.202 (n=12) | +0.00 | +0.00 | +0.72 | $0.0033 | 0 |

Pass rate by family (mean over cases of the per-case rep average):

| arm | audit | capture | maintain | restrain |
| --- | ---: | ---: | ---: | ---: |
| control | 1.00 | 0.67 | 1.00 | 1.00 |
| lean | 0.56 | 0.89 | 0.78 | 1.00 |
| principled | 0.67 | 0.67 | 0.89 | 1.00 |
| procedural | 0.33 | 0.67 | 0.89 | 0.89 |
| examples | 0.67 | 0.78 | 0.78 | 1.00 |
| newcomer | 0.44 | 0.67 | 0.89 | 0.78 |

#### comment-edit-haiku-regraded — split: all

| arm | pass | Δpass vs control (95% CI) | Δbehavior | Δbad_claims | Δnoise_lines | cost/attempt | errors |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| control | 0.850 | — | — | — | — | $0.0019 | 0 |
| lean | 0.833 | -0.017 ± 0.167 (n=20) | +0.00 | +0.02 | -0.42 | $0.0024 | 0 |
| principled | 0.833 | -0.017 ± 0.153 (n=20) | +0.00 | +0.00 | +0.03 | $0.0030 | 0 |
| procedural | 0.733 | -0.117 ± 0.197 (n=20) | +0.00 | +0.00 | +0.20 | $0.0034 | 0 |
| examples | 0.783 | -0.067 ± 0.181 (n=20) | +0.00 | +0.00 | +0.02 | $0.0031 | 0 |
| newcomer | 0.767 | -0.083 ± 0.170 (n=20) | +0.00 | +0.00 | +0.37 | $0.0033 | 0 |

Pass rate by family (mean over cases of the per-case rep average):

| arm | audit | capture | maintain | restrain |
| --- | ---: | ---: | ---: | ---: |
| control | 0.80 | 0.60 | 1.00 | 1.00 |
| lean | 0.53 | 0.93 | 0.87 | 1.00 |
| principled | 0.73 | 0.73 | 0.87 | 1.00 |
| procedural | 0.47 | 0.73 | 0.80 | 0.93 |
| examples | 0.67 | 0.73 | 0.73 | 1.00 |
| newcomer | 0.47 | 0.80 | 0.93 | 0.87 |

