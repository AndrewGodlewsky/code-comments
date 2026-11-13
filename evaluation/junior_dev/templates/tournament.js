// Junior-dev tournament batch. build.py prepends `export const meta`, `const DATA = {...}` and
// render.js, so this file is not runnable on its own. Every role is an agent that is told to use no
// tools; what each role may see is decided here (design: Behaviour step 2, Measures, Keeping it honest).

const TAGS = new Set(['checked', 'decided', 'unknown'])
const STR = { type: 'string' }
const ARTIFACT_SCHEMA = { type: 'object', properties: { artifact: STR }, required: ['artifact'] }
const REVISE_SCHEMA = { type: 'object', properties: { artifact: STR, changes: { type: 'array', items: STR } }, required: ['artifact', 'changes'] }
const QUESTIONS_SCHEMA = DATA.schemas.questions
const TEACHBACK_SCHEMA = DATA.schemas.teachback
const AUTHOR_SCHEMA = {
  type: 'object',
  properties: {
    artifact: STR,
    answers: { type: 'array', items: { type: 'object', properties: { id: STR, tag: { type: 'string', enum: ['checked', 'decided', 'unknown'] }, text: STR }, required: ['id', 'tag', 'text'] } },
    changes: { type: 'array', items: STR },
  },
  required: ['artifact', 'answers', 'changes'],
}
const VERDICT_SCHEMA = { type: 'object', properties: { correct: { type: 'boolean' }, misreadings: { type: 'array', items: STR }, artifact: STR }, required: ['correct', 'misreadings', 'artifact'] }
const CRITIC_SCHEMA = { type: 'object', properties: { critiques: { type: 'array', items: STR }, done: { type: 'boolean' } }, required: ['critiques', 'done'] }
const KEY_SCHEMA = { type: 'object', properties: { answers: { type: 'array', items: { type: 'object', properties: { id: STR, answer: STR, decided: { type: 'boolean' } }, required: ['id', 'answer', 'decided'] } } }, required: ['answers'] }
const READER_SCHEMA = { type: 'object', properties: { answers: { type: 'array', items: { type: 'object', properties: { id: STR, answer: STR }, required: ['id', 'answer'] } } }, required: ['answers'] }
const GRADES_SCHEMA = { type: 'object', properties: { grades: { type: 'array', items: { type: 'object', properties: { reader: STR, id: STR, correct: { type: 'boolean' } }, required: ['reader', 'id', 'correct'] } } }, required: ['grades'] }
const CHECK_SCHEMA = {
  type: 'object',
  properties: {
    requirements: { type: 'array', items: { type: 'object', properties: { id: STR, present: { type: 'boolean' } }, required: ['id', 'present'] } },
    honesty: { type: 'array', items: { type: 'object', properties: { point: STR, reported_as_hole: { type: 'boolean' }, invented: { type: 'boolean' } }, required: ['point', 'reported_as_hole', 'invented'] } },
  },
  required: ['requirements', 'honesty'],
}
const P = DATA.prompts
const ROLE = (text) => 'SYSTEM INSTRUCTIONS FOR YOUR ROLE:\n\n' + text.trim() + '\n\n---\n\n'

function context(c) {
  let out = '# The brief\n\n' + c.brief.trim() + '\n'
  const paths = Object.keys(c.existing || {})
  if (paths.length) {
    out += '\n# Existing files\n'
    for (const p of paths) out += `\n## ${p}\n\n\`\`\`\n${c.existing[p].replace(/\s+$/, '')}\n\`\`\`\n`
  }
  return out
}

// The tournament's authors return whole documents, unlike the plugin's, which edit a file on disk.
// A model can return a placeholder ("Unchanged: the document as given above") or a fragment instead;
// accepting it would silently replace the plan, as happened once in climb-01. Keep the current
// document unless the new one is at least 30% of its length.
function accept(run, role, current, proposed) {
  const words = s => (String(s || '').match(/\w+/g) || []).length
  if (!proposed || !proposed.trim()) return current
  // A document that arrives as one line full of literal \n escapes (seen once, from a Haiku author)
  // is decoded back into lines; a real document has real line breaks.
  if ((proposed.match(/\n/g) || []).length <= 2 && (proposed.match(/\\n/g) || []).length >= 5) {
    proposed = proposed.replace(/\\r\\n|\\n/g, '\n').replace(/\\t/g, '\t').replace(/\\"/g, '"')
  }
  if (words(current) > 100 && words(proposed) < 0.3 * words(current)) {
    run.errors.push(`${role}: rejected a ${words(proposed)}-word artifact that would replace ${words(current)} words`)
    return current
  }
  return proposed
}

function questionList(items) {
  return items.map(q => `Q${q.id} (about: ${q.about}): ${q.text}`).join('\n')
}

async function call(run, role, prompt, opts, extra) {
  const label = `${role}|${run.run_id}${extra ? '|' + extra : ''}`
  const out = await agent(prompt, Object.assign({}, opts, { label, phase: run.arm }))
  const u = run.usage.roles[role] || (run.usage.roles[role] = { model: opts.model || 'inherit', in: 0, out: 0, calls: 0 })
  u.in += prompt.length
  u.out += out ? JSON.stringify(out).length : 0
  u.calls += 1
  if (!out) run.errors.push(`${role}: no result`)
  return out
}

async function selfReview(run, c, arm, art) {
  for (let pass = 1; pass <= arm.self_passes; pass++) {
    const s = await call(run, 'self', P.selfreview + '\n\n' + context(c) + '\n# Your document\n\n' + art, { model: run.author, schema: REVISE_SCHEMA })
    if (!s) break
    run.rounds = pass
    art = accept(run, 'self', art, s.artifact)
    run.changes.push(...(s.changes || []).map(String))
    if (!(s.changes || []).length) break
  }
  run.end_reason = run.end_reason || 'passes'
  return art
}

async function critic(run, c, arm, art) {
  for (let r = 1; r <= arm.rounds; r++) {
    const k = await call(run, 'critic', ROLE(P.critic) + '# The document\n\n' + art, { model: arm.junior_model, schema: CRITIC_SCHEMA })
    if (!k || !(k.critiques || []).length) { run.end_reason = k ? 'critic-done' : 'error'; break }
    run.rounds = r
    const points = k.critiques.map((x, i) => `${i + 1}. ${x}`).join('\n')
    const v = await call(run, 'critic-revise', P.critic_revise + '\n\n' + context(c) + '\n# Your document\n\n' + art + '\n\n# The reviewer\'s points\n\n' + points, { model: run.author, schema: REVISE_SCHEMA })
    if (!v) { run.end_reason = 'error'; break }
    art = accept(run, 'critic-revise', art, v.artifact)
    run.changes.push(...(v.changes || []).map(String))
  }
  run.end_reason = run.end_reason || 'cap'
  return art
}

// Skill step 7: one simplify pass over the whole file. Given the transcript (the rewrite-before-teach-back
// order), the author also sees every question and answer, to use as its checklist.
async function simplifyPass(run, c, arm, art, transcript) {
  const qa = transcript && transcript.length ? '\n# The junior\'s questions and your answers\n\n' + renderTranscript(transcript) : ''
  // The rewrite-before-teach-back skill numbers this step 6 (v5); the original order numbers it 7.
  const lead = arm.simplify_at === 'before_teachback' ? P.author_rewrite : P.author_simplify
  const first = arm.first_version ? '\n# The first version of your document\n\n' + run.artifact_initial.trim() + '\n' : ''
  const s = await call(run, 'simplify', lead + '\n\n# The skill\n\n' + arm.skill_text.trim() + '\n\n' + context(c) +
    first + '\n# Your document\n\n' + art.trim() + '\n' + qa, { model: run.author, schema: REVISE_SCHEMA })
  if (!s) return art
  run.changes.push(...(s.changes || []).map(String))
  return accept(run, 'simplify', art, s.artifact)
}

function authorPrompt(c, arm, art, transcript, numbered) {
  return P.author_junior + '\n\n# The skill\n\n' + arm.skill_text.trim() + '\n\n' + context(c) +
    '\n# Your document (current version)\n\n' + art.trim() + '\n' +
    (transcript.length ? '\n# Earlier rounds\n\n' + renderTranscript(transcript) : '') +
    '\n# The junior\'s questions this round\n\n' + questionList(numbered) + '\n'
}

async function juniorLoop(run, c, arm, art) {
  let round = 0, nextId = 1, phase = 'asking', wrong = 0, rewritten = false
  const early = arm.final_simplify && arm.simplify_at === 'before_teachback'
  for (let guard = 0; guard < 50; guard++) {
    if (phase === 'teachback' && early && !rewritten) {
      art = await simplifyPass(run, c, arm, art, run.transcript)
      rewritten = true
    }
    if (phase === 'asking') {
      if (round >= arm.rounds) { run.end_reason = 'cap'; break }
      const brief = arm.review === 'junior_full' ? DATA.framing.brief_header + c.brief.trim() + '\n\n' : ''
      const j = await call(run, 'junior', ROLE(arm.junior_text) + brief + renderJunior(art, run.transcript), { model: arm.junior_model, schema: QUESTIONS_SCHEMA })
      if (!j) { run.end_reason = 'error'; break }
      const asked = (j.questions || []).filter(q => q && String(q.text || '').trim())
      if (!asked.length) {
        if (arm.teachback === 'none') { run.end_reason = 'junior-done'; break }
        phase = 'teachback'
        continue
      }
      round += 1
      const numbered = asked.map((q, i) => ({ id: String(nextId + i), text: String(q.text).trim(), about: String(q.about || '').trim() || 'general' }))
      nextId += numbered.length
      const a = await call(run, 'author', authorPrompt(c, arm, art, run.transcript, numbered), { model: run.author, schema: AUTHOR_SCHEMA })
      if (!a) { run.end_reason = 'error'; break }
      const ids = new Set(numbered.map(q => q.id))
      // Authors label answers "Q7" as the skill shows; junior.py's parser accepts the prefix, so this must too.
      const normId = x => String(x.id).trim().replace(/^Q/i, '')
      const answers = (a.answers || []).filter(x => ids.has(normId(x))).map(x => ({
        id: normId(x), tag: TAGS.has(String(x.tag).toLowerCase()) ? String(x.tag).toLowerCase() : 'decided', text: String(x.text || '').trim(),
      }))
      run.transcript.push({ round, questions: numbered, answers })
      for (const x of answers) if (x.tag === 'unknown') run.holes.push(`Q${x.id}: ${numbered.find(q => q.id === x.id).text} (author: ${x.text})`)
      run.changes.push(...(a.changes || []).map(String))
      art = accept(run, 'author', art, a.artifact)
    } else {
      const message = arm.teachback === 'same' ? renderTeachbackSame(art, run.transcript) : renderTeachback(art)
      const t = await call(run, 'teachback', ROLE(arm.teachback_text) + message, { model: arm.junior_model, schema: TEACHBACK_SCHEMA })
      if (!t) { run.end_reason = 'error'; break }
      const gaps = (t.gaps || []).map(String)
      const v = await call(run, 'verdict', P.author_verdict + '\n\n# The skill\n\n' + arm.skill_text.trim() + '\n\n' + context(c) +
        '\n# Your document\n\n' + art.trim() + '\n\n# The fresh junior\'s explanation\n\n' + t.explanation +
        (gaps.length ? '\n\nThey could not explain:\n' + gaps.map(g => '- ' + g).join('\n') : ''), { model: run.author, schema: VERDICT_SCHEMA })
      if (!v) { run.end_reason = 'error'; break }
      run.teachbacks.push({ text: t.explanation, gaps, verdict: v.correct ? 'correct' : 'wrong', notes: (v.misreadings || []).join('; ') })
      if (!v.correct) art = accept(run, 'verdict', art, v.artifact)
      if (v.correct) { run.end_reason = 'teachback-correct'; break }
      wrong += 1
      if (wrong >= DATA.max_teachbacks) { run.end_reason = 'teachbacks'; break }
      if (round >= arm.rounds) { run.end_reason = 'cap'; break }
      phase = 'asking'
    }
  }
  // A loop that ended without reaching a teach-back (round cap, error) still gets its one rewrite.
  if (early && !rewritten) art = await simplifyPass(run, c, arm, art, run.transcript)
  run.rounds = round
  return art
}

function keysFor(run, c) {
  // brief items: the case key; design items: the author's sealed answer in natural mode, the case key otherwise.
  const keys = {}, excluded = []
  for (const q of c.quiz) {
    if (q.kind === 'brief' || run.mode !== 'natural') keys[q.id] = q.key
    else if (run.author_key[q.id] && run.author_key[q.id].decided && run.author_key[q.id].answer.trim()) keys[q.id] = run.author_key[q.id].answer
    else excluded.push(q.id)
  }
  return { keys, excluded }
}

async function runOne(spec) {
  const c = DATA.cases[spec.case], arm = DATA.arms[spec.arm]
  const run = Object.assign({}, spec, {
    skill_rev: DATA.skill_rev, label: DATA.label, artifact_initial: '', artifact_final: '', transcript: [], teachbacks: [],
    changes: [], holes: [], rounds: 0, end_reason: null, author_key: {}, reader_answers: {}, grades: {}, grades_by_model: {},
    excluded: [], requirements: [], honesty: [], usage: { roles: {} }, errors: [],
  })
  if (spec.mode === 'natural') {
    const extra = arm.review === 'prompt' ? '\n' + DATA.junior_prompt_line + '\n' : ''
    const d = await call(run, 'draft', P.author_draft + '\n\n' + context(c) + extra, { model: spec.author, schema: ARTIFACT_SCHEMA })
    if (!d || !d.artifact) return run
    run.artifact_initial = d.artifact
  } else {
    run.artifact_initial = c.start[spec.mode]
  }
  let art = run.artifact_initial
  if (arm.review === 'self') art = await selfReview(run, c, arm, art)
  else if (arm.review === 'critic') art = await critic(run, c, arm, art)
  else if (arm.review === 'junior' || arm.review === 'junior_full') {
    art = await juniorLoop(run, c, arm, art)
    if (arm.final_simplify && arm.simplify_at === 'end') art = await simplifyPass(run, c, arm, art)
  }
  else if (arm.review === 'simplify') {
    // Control: the skill's final pass (step 7) on the first draft, with no junior loop. It isolates
    // what the questions add beyond a good final pass.
    art = await simplifyPass(run, c, arm, art)
    run.end_reason = 'simplify-only'
  }
  else run.end_reason = 'none'
  run.artifact_final = art

  if (spec.mode === 'natural') {
    const design = c.quiz.filter(q => q.kind === 'design')
    const k = await call(run, 'key', P.author_key + '\n\n' + context(c) +
      (run.transcript.length ? '\n# Your review with the junior\n\n' + renderTranscript(run.transcript) : '') +
      '\n# Your final document\n\n' + art.trim() + '\n\n# Questions\n\n' + design.map(q => `${q.id}: ${q.question}`).join('\n'),
      { model: spec.author, schema: KEY_SCHEMA })
    for (const a of (k && k.answers) || []) run.author_key[String(a.id)] = { answer: String(a.answer || ''), decided: !!a.decided }
  }
  const { keys, excluded } = keysFor(run, c)
  run.excluded = excluded
  const questions = c.quiz.map(q => `${q.id}: ${q.question}`).join('\n')
  const readerOuts = await parallel(DATA.readers.map(r => () => call(run, 'reader',
    ROLE(P.reader + (r.short ? '\n\n' + P.reader_short : '')) + '# The document\n\n' + art.trim() + '\n\n# Questions\n\n' + questions,
    Object.assign({ model: r.model, schema: READER_SCHEMA }, r.effort ? { effort: r.effort } : {}), r.name)))
  DATA.readers.forEach((r, i) => {
    run.reader_answers[r.name] = {}
    for (const a of (readerOuts[i] && readerOuts[i].answers) || []) run.reader_answers[r.name][String(a.id)] = String(a.answer || '')
  })
  const items = c.quiz.filter(q => keys[q.id] !== undefined).map(q =>
    `### ${q.id}\nQuestion: ${q.question}\nKey: ${keys[q.id]}\n` + DATA.readers.map(r => `Reader ${r.name}: ${run.reader_answers[r.name][q.id] || 'NOT STATED'}`).join('\n')).join('\n\n')
  const gradeOuts = await parallel(DATA.grader_models.map(m => () => call(run, 'grader', ROLE(P.grader) + items, { model: m, effort: 'low', schema: GRADES_SCHEMA }, m)))
  DATA.grader_models.forEach((m, i) => {
    const byReader = {}
    for (const g of (gradeOuts[i] && gradeOuts[i].grades) || []) (byReader[g.reader] = byReader[g.reader] || []).push({ id: String(g.id), correct: !!g.correct })
    run.grades_by_model[m] = byReader
  })
  run.grades = run.grades_by_model[DATA.grader_models[0]] || {}
  const ck = await call(run, 'checker', ROLE(P.checker) + '# Requirements\n\n' + c.requirements.map(r => `${r.id}: ${r.text}`).join('\n') +
    '\n\n# Undecided points\n\n' + ((c.undecided || []).map(u => '- ' + u.point).join('\n') || '(none)') +
    '\n\n# The document\n\n' + art.trim() + (run.holes.length ? '\n\n# The author\'s open questions\n\n' + run.holes.map(h => '- ' + h).join('\n') : ''),
    { model: 'sonnet', effort: 'low', schema: CHECK_SCHEMA })
  run.requirements = (ck && ck.requirements) || []
  run.honesty = (ck && ck.honesty) || []
  return run
}

phase('Runs')
const results = await pipeline(DATA.runs, spec => runOne(spec))
const failed = results.filter(r => !r).length
if (failed) log(`${failed} runs threw and are missing from the results`)
return { label: DATA.label, skill_rev: DATA.skill_rev, runs: results }
