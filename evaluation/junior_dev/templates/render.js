// Message renderers for the junior and the teach-back. They must produce exactly what
// plugins/junior-dev/scripts/junior.py's build_junior_message and build_teachback_message produce,
// from the same framing constants (DATA.framing), so the tournament tests the shipped framing.
// tests/test_junior_dev_harness.py::test_js_render_matches_python holds them to that.

function renderTranscript(transcript) {
  const parts = []
  for (const rnd of transcript) {
    const answers = {}
    for (const a of rnd.answers || []) answers[a.id] = a
    const lines = [`## Round ${rnd.round}`, '']
    for (const q of rnd.questions) {
      lines.push(`Q${q.id} (about: ${q.about}): ${q.text}`)
      const a = answers[q.id]
      lines.push(a ? `A${q.id} [${a.tag}]: ${a.text}` : `A${q.id}: (no answer)`)
      lines.push('')
    }
    parts.push(lines.join('\n'))
  }
  return parts.join('\n')
}

function renderJunior(artifact, transcript) {
  let message = DATA.framing.artifact_header + artifact.trim() + '\n'
  if (transcript.length) message += DATA.framing.transcript_header + renderTranscript(transcript)
  return message + DATA.framing.ask
}

function renderTeachback(artifact) {
  return DATA.framing.teachback_header + artifact.trim() + '\n' + DATA.framing.teachback_instruction
}

// Eval-only variant: the "same junior" teach-back, which also sees this loop's questions and answers.
function renderTeachbackSame(artifact, transcript) {
  return DATA.framing.teachback_header + artifact.trim() + '\n' +
    (transcript.length ? DATA.framing.transcript_header + renderTranscript(transcript) : '') +
    DATA.framing.teachback_instruction
}
