export const meta = {
  name: 'junior-dev-cases',
  description: 'Write planning-clarity benchmark cases from slots, check each independently, rewrite once on failure',
  phases: [
    { title: 'Write', detail: 'one writer per slot' },
    { title: 'Check', detail: 'independent checker per case' },
    { title: 'Rewrite', detail: 'one rewrite and recheck for failing cases' },
  ],
}

// args: { slots: [...], avoid?: "text describing existing cases to differ from" }
// The writers and checkers are told only about a planning-clarity benchmark. They never see
// the junior-dev skill or its prompts, so the cases cannot be tuned to it (design: keeping the test honest).

const FORMATS = {
  'mermaid-sequence': 'a Mermaid sequenceDiagram, with short notes before or after it',
  'mermaid-flowchart': 'a Mermaid flowchart, with short notes before or after it',
  'mermaid-state': 'a Mermaid stateDiagram-v2, with short notes before or after it',
  'mermaid-er': 'a Mermaid erDiagram, with short notes on how the design works',
  'ascii': 'an ASCII diagram in a fenced code block, with short notes',
  'prose-steps': 'a numbered, step-by-step plan in Markdown',
  'checklist': 'a Markdown checklist of steps, in the order they are done',
}

const CASE_SCHEMA = {
  type: 'object',
  properties: {
    brief: { type: 'string' },
    existing_files: { type: 'array', items: { type: 'object', properties: { path: { type: 'string' }, content: { type: 'string' } }, required: ['path', 'content'] } },
    undecided: { type: 'array', items: { type: 'object', properties: { point: { type: 'string' }, how_brief_says_it: { type: 'string' } }, required: ['point', 'how_brief_says_it'] } },
    quiz: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, kind: { type: 'string', enum: ['brief', 'design'] }, question: { type: 'string' }, key: { type: 'string' }, why: { type: 'string' } }, required: ['id', 'kind', 'question', 'key', 'why'] } },
    requirements: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, text: { type: 'string' } }, required: ['id', 'text'] } },
    reference_artifact: { type: 'string' },
    seeded_presentation: { type: 'string' },
    seeded_implicit: { type: 'string' },
  },
  required: ['brief', 'existing_files', 'undecided', 'quiz', 'requirements', 'reference_artifact', 'seeded_presentation', 'seeded_implicit'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: { ok: { type: 'boolean' }, problems: { type: 'array', items: { type: 'string' } } },
  required: ['ok', 'problems'],
}

const BENCHMARK = `You are helping build a planning-clarity benchmark for AI coding models. In each case, a model is given a brief (and sometimes a few files describing the existing system) and asked to write a plan or diagram in a stated format. Later, reader models who see ONLY that plan or diagram (not the brief, not the files) answer a hidden quiz about how the system works. The benchmark measures how clearly a plan or diagram communicates its design to a smart, technical reader who does not know the project or the stack. Use no tools; reply only with the structured result.`

function writerPrompt(slot) {
  const fmt = FORMATS[slot.format]
  return `${BENCHMARK}

Write ONE case for this slot:
- id: ${slot.id}; family: ${slot.family}; complexity: ${slot.complexity}
- topic: ${slot.topic}
- requested format: ${fmt}
- existing-system files: ${slot.existing ? 'YES: include 1 to 3 small files (code or docs, 120 lines in total at most) that describe the current system the plan must build on. The brief must point the author to them by path (existing/<name>). Readers never see these files, so anything a reader needs from them must end up in a good artifact.' : 'none (existing_files must be an empty list)'}
- deliberately undecided point: ${slot.undecided ? 'YES: leave exactly one point undecided on purpose, and have the brief say plainly that it has not been decided yet (for example "Product has not decided X yet"). A good artifact marks it as open; it does not invent an answer. Record it in undecided.' : 'none (undecided must be an empty list)'}
${args.avoid ? `- make this case clearly different from these existing cases: ${args.avoid}` : ''}

Fields:
- brief: Markdown, 150 to 450 words, written the way a tech lead briefs an engineer: the goal, the requirements and constraints that are fixed, anything about the existing system, and the requested format (say it explicitly). Fix enough facts (limits, timings, ordering rules, failure behaviour) that some quiz items have a single right answer. Do not include any quiz question word for word.
- quiz: 8 to 12 items about HOW THE SYSTEM WORKS: flows, ordering, what triggers what, what data moves, who owns or stores state, what happens on failure or retry. No trivia (names of steps, counts of boxes).
  - kind "brief": a fact the brief or the existing files settle, that a clear artifact must convey. key: the short, unambiguous answer.
  - kind "design": a choice the brief leaves open, that ANY valid design must still answer (for example "Where is the session state stored, and what removes it on logout?"). Word it so a different but valid design can answer it too. key: the answer according to your reference_artifact.
  - At least 4 design items. Ids q1, q2, ...
  - why: one line on why a reader needs this to understand the design.
- requirements: 4 to 8 items any acceptable artifact must contain, taken from the brief. Ids r1, r2, ...
- reference_artifact: the artifact an excellent engineer would write, in the requested format: simple, cleanly laid out, step by step. It says what starts each step, what moves, where the state lives and what happens on failure. A reader with only this artifact must be able to answer EVERY quiz item. If there is an undecided point, the artifact marks it as an open question. Mermaid must be valid Mermaid 11 syntax.
- seeded_presentation: the SAME design and information as the reference (every quiz answer is still somewhere in it), but badly presented: jumbled order, mixed levels of detail, inconsistent names for the same thing, long run-on paragraphs, and for diagrams a cluttered or poorly labelled (still valid) diagram with key facts pushed into scattered notes. Nothing false, nothing removed.
- seeded_implicit: the same design, written the way a hurried engineer often writes it: the components and steps are named, but how they connect, what triggers what, where state lives and what happens on failure are left implicit or only hinted at. Nothing false. Many quiz answers should now be hard or impossible to get from it.`
}

function checkerPrompt(slot, c) {
  return `${BENCHMARK}

You are an independent, strict checker of one case (slot ${slot.id}: ${slot.topic}; requested format: ${FORMATS[slot.format]}; existing files expected: ${slot.existing}; undecided point expected: ${slot.undecided}).

Check every rule and report concrete problems:
1. The brief states the requested format, fixes enough facts, and contains no quiz question word for word.
2. Each "brief" quiz item is settled by the brief or existing files, and its key is short and unambiguous.
3. Each "design" item is a choice the brief leaves open, worded so that a different valid design could still answer it. There are at least 4 design items and 8 to 12 items in total.
4. Quiz items ask how the system works (flows, ordering, triggers, data, state, failure), not trivia.
5. A reader who sees ONLY reference_artifact can answer every item, and the answer matches the key.
6. reference_artifact is clear, in the requested format, and Mermaid (if any) is valid Mermaid 11 syntax.
7. seeded_presentation keeps every quiz answer recoverable but is clearly worse presented. seeded_implicit is not false, and it leaves several quiz answers implicit or missing.
8. Existing files and the undecided point are present exactly as the slot expects. A brief with an undecided point says plainly that it is undecided, and the reference marks it as open.
9. requirements has 4 to 8 items, all from the brief.

Set ok to true only if there is no problem that would make the case unfair or unmeasurable. List each problem as one specific, fixable sentence.

CASE (JSON):
${JSON.stringify(c, null, 1)}`
}

function rewritePrompt(slot, c, problems) {
  return `${writerPrompt(slot)}

A checker found these problems with your earlier version. Return the full corrected case, fixing every one:
${problems.map(p => '- ' + p).join('\n')}

EARLIER VERSION (JSON):
${JSON.stringify(c, null, 1)}`
}

const results = await pipeline(
  args.slots,
  (slot) => agent(writerPrompt(slot), { label: `write:${slot.id}`, phase: 'Write', schema: CASE_SCHEMA }),
  (c, slot) => c ? agent(checkerPrompt(slot, c), { label: `check:${slot.id}`, phase: 'Check', schema: VERDICT_SCHEMA }).then(v => ({ c, v })) : null,
  async (r, slot) => {
    if (!r) return { slot, ok: false, problems: ['writer returned nothing'], rewritten: false }
    if (r.v && r.v.ok) return { slot, ok: true, case: r.c, problems: r.v.problems, rewritten: false }
    const c2 = await agent(rewritePrompt(slot, r.c, r.v ? r.v.problems : ['checker returned nothing']), { label: `rewrite:${slot.id}`, phase: 'Rewrite', schema: CASE_SCHEMA })
    if (!c2) return { slot, ok: false, case: r.c, problems: r.v ? r.v.problems : [], rewritten: true }
    const v2 = await agent(checkerPrompt(slot, c2), { label: `recheck:${slot.id}`, phase: 'Rewrite', schema: VERDICT_SCHEMA })
    return { slot, ok: !!(v2 && v2.ok), case: c2, problems: v2 ? v2.problems : ['recheck returned nothing'], first_problems: r.v ? r.v.problems : [], rewritten: true }
  },
)

const kept = results.filter(r => r && r.ok)
const dropped = results.filter(r => !r || !r.ok)
log(`${kept.length} cases passed the checker; ${dropped.length} dropped: ${dropped.map(r => r ? r.slot.id : '?').join(', ') || 'none'}`)
return { cases: kept.map(r => ({ slot: r.slot, case: r.case, notes: r.problems, rewritten: r.rewritten })), dropped }
