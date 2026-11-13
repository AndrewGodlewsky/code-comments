// Offline dry run of a built Junior-dev batch: executes the workflow script with stub agent(),
// pipeline() and parallel() that return canned results by role, and logs every prompt. Used by
// tests/test_junior_dev_harness.py to check what each role is shown, without calling a model.
//
//   node dryrun.mjs <built-batch.js>      -> {"result": ..., "prompts": [{label, role, run, arm, prompt, opts}]}
//   node dryrun.mjs --render < input.json -> {"text": ...}   (render.js only; input: kind, artifact, transcript, framing, render)
import fs from 'fs'

const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const readStdin = () => fs.readFileSync(0, 'utf8')

if (process.argv[2] === '--render') {
  const input = JSON.parse(readStdin())
  const body = `const DATA = { framing: ${JSON.stringify(input.framing)} };\n` + fs.readFileSync(input.render, 'utf8') +
    `\nreturn kind === 'junior' ? renderJunior(artifact, transcript) : renderTeachback(artifact)`
  const fn = new AsyncFunction('kind', 'artifact', 'transcript', body)
  const text = await fn(input.kind, input.artifact, input.transcript)
  process.stdout.write(JSON.stringify({ text }))
  process.exit(0)
}

const source = fs.readFileSync(process.argv[2], 'utf8').replace(/^export const meta/m, 'const meta')
const dataLine = source.split('\n').find(l => l.startsWith('const DATA = '))
const DATA = JSON.parse(dataLine.slice('const DATA = '.length))
const armOf = Object.fromEntries((DATA.runs || []).map(r => [r.run_id, r.arm]))
const prompts = []
const juniorCalls = {}
const ids = (n, prefix = 'q') => Array.from({ length: n }, (_, i) => `${prefix}${i + 1}`)
// Canned artifacts carry only the case id, never the run id (which names the arm), so blind-judge tests mean something.
const caseOf = run => String(run).split('__')[0]

function canned(role, run, prompt) {
  switch (role) {
    case 'draft': return { artifact: `DRAFT for ${caseOf(run)}\n1. A step.\n` }
    case 'junior': {
      juniorCalls[run] = (juniorCalls[run] || 0) + 1
      return juniorCalls[run] === 1
        ? { questions: [{ id: 'q1', text: 'STUB-QUESTION one?', about: 'step 1' }, { id: 'q2', text: 'STUB-QUESTION two?', about: 'step 2' }], done: false }
        : { questions: [], done: true }
    }
    case 'author': return { artifact: `REVISED for ${caseOf(run)}\n1. A step.\n2. Clarified.\n`, answers: [{ id: 'Q1', tag: 'checked', text: 'ans one' }, { id: 'Q2', tag: 'unknown', text: 'not decided' }], changes: ['clarified step 2'] }
    case 'teachback': return { explanation: 'Step 1 happens, then step 2.', gaps: [] }
    case 'verdict': return { correct: true, misreadings: [], artifact: '' }
    case 'key': return { answers: ids(8).slice(4).map((id, i) => ({ id, answer: `author answer ${id}`, decided: i < 3 })) }
    case 'reader': return { answers: ids(8).map(id => ({ id, answer: `reader answer ${id}` })) }
    case 'grader': return { grades: ['haiku-low', 'sonnet'].flatMap(reader => ids(8).map((id, i) => ({ reader, id, correct: i % 2 === 0 }))) }
    case 'checker': return { requirements: ids(4, 'r').map(id => ({ id, present: true })), honesty: [{ point: 'session length', reported_as_hole: true, invented: false }] }
    case 'self': return { artifact: `SELF for ${caseOf(run)}\n1. A step.\n`, changes: [] }
    case 'critic': return { critiques: [], done: true }
    case 'critic-revise': return { artifact: `CRITIC-REVISED for ${caseOf(run)}\n`, changes: ['x'] }
    case 'judge': return { winner: 'A', reason: 'stub' }
    default: throw new Error(`no canned result for role ${role}`)
  }
}

async function agent(prompt, opts = {}) {
  const [role, run] = String(opts.label || '').split('|')
  prompts.push({ label: opts.label, role, run, arm: armOf[run], prompt, opts: { model: opts.model, effort: opts.effort } })
  return canned(role, run, prompt)
}
async function parallel(thunks) {
  return Promise.all(thunks.map(t => t().catch(() => null)))
}
async function pipeline(items, ...stages) {
  const out = []
  for (let i = 0; i < items.length; i++) {
    let value = items[i]
    try {
      for (const stage of stages) value = await stage(value, items[i], i)
    } catch (e) {
      process.stderr.write(`stage threw for item ${i}: ${e.stack}\n`)
      value = null
    }
    out.push(value)
  }
  return out
}
const log = () => {}
const phase = () => {}
const budget = { total: null, spent: () => 0, remaining: () => Infinity }

const body = source
const fn = new AsyncFunction('agent', 'pipeline', 'parallel', 'log', 'phase', 'args', 'budget', body)
const result = await fn(agent, pipeline, parallel, log, phase, undefined, budget)
process.stdout.write(JSON.stringify({ result, prompts }))
