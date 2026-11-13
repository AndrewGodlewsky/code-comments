// Parse Mermaid sources with Mermaid 11 under jsdom. stdin: JSON array of sources;
// stdout: JSON array of {ok, error}. Usage: node check.mjs <this directory>
import { createRequire } from 'module'
import { pathToFileURL } from 'url'
import path from 'path'
import fs from 'fs'
const dir = process.argv[2]
const require = createRequire(path.join(dir, 'package.json'))
const { JSDOM } = require('jsdom')
const dom = new JSDOM('<!doctype html><html><body></body></html>')
globalThis.window = dom.window
globalThis.document = dom.window.document
globalThis.DOMParser = dom.window.DOMParser
globalThis.Element = dom.window.Element
const core = path.join(dir, 'node_modules', 'mermaid', 'dist', 'mermaid.core.mjs')
const { default: mermaid } = await import(pathToFileURL(core).href)
mermaid.initialize({ startOnLoad: false })
const sources = JSON.parse(fs.readFileSync(0, 'utf8'))
const out = []
for (const src of sources) {
  try { await mermaid.parse(src); out.push({ ok: true }) }
  catch (e) { out.push({ ok: false, error: String(e.message || e).split('\n').slice(0, 3).join(' ') }) }
}
process.stdout.write(JSON.stringify(out))
