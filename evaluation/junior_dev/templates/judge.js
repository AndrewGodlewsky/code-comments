// Junior-dev blind pairwise clarity judge. build.py prepends `export const meta` and `const DATA`.
// Each pair of final artifacts (same case, author, mode and repeat; two arms) is judged twice, once in
// each order, by a judge that sees only the two documents: no brief, no arm names (research E1).

const JUDGE_SCHEMA = {
  type: 'object',
  properties: { winner: { type: 'string', enum: ['A', 'B', 'tie'] }, reason: { type: 'string' } },
  required: ['winner', 'reason'],
}

async function judgeOne(p) {
  const prompt = 'SYSTEM INSTRUCTIONS FOR YOUR ROLE:\n\n' + DATA.prompt.trim() + '\n\n---\n\n# Document A\n\n' +
    p.doc_a.trim() + '\n\n# Document B\n\n' + p.doc_b.trim() + '\n'
  const out = await agent(prompt, { label: `judge|${p.pair_id}|${p.order}`, phase: 'Judge', model: DATA.judge_model, schema: JUDGE_SCHEMA })
  const winner = out ? out.winner : null
  const arm = winner === 'tie' ? 'tie' : winner === 'A' ? (p.order === 'ab' ? p.arm_a : p.arm_b)
    : winner === 'B' ? (p.order === 'ab' ? p.arm_b : p.arm_a) : null
  return { pair_id: p.pair_id, case: p.case, author: p.author, mode: p.mode, rep: p.rep, arm_a: p.arm_a, arm_b: p.arm_b,
    order: p.order, winner, winner_arm: arm, reason: out ? out.reason : null, words_a: p.words_a, words_b: p.words_b,
    judge_model: DATA.judge_model }
}

phase('Judge')
const judgments = await pipeline(DATA.pairs, p => judgeOne(p))
return { label: DATA.label, judgments }
