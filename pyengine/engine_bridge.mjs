import * as engine from '../engine/pkg/hexchess_engine.js'
import { readFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const wasmPath = join(__dirname, '..', 'engine', 'pkg', 'hexchess_engine_bg.wasm')

let initPromise = null

async function ensureInitialized() {
  if (!initPromise) {
    initPromise = readFile(wasmPath)
      .then((bytes) => engine.default({ module_or_path: bytes }))
  }

  await initPromise
}

function parseInput(raw) {
  try {
    return JSON.parse(raw || '{}')
  } catch {
    return {}
  }
}

function createError(message) {
  return {
    error: {
      message,
    },
  }
}

async function main() {
  const chunks = []

  for await (const chunk of process.stdin) {
    chunks.push(chunk)
  }

  const request = parseInput(Buffer.concat(chunks).toString('utf-8'))

  try {
    await ensureInitialized()

    const command = request?.command
    const options = request?.options ?? {}

    if (command === 'hexchess/ping') {
      process.stdout.write(JSON.stringify({
        command,
        options,
        response: {
          now: Date.now(),
        },
      }))
      return
    }

    if (command === 'hexchess/evaluate') {
      process.stdout.write(JSON.stringify({
        command,
        options,
        response: engine.evaluate(options),
      }))
      return
    }

    process.stdout.write(JSON.stringify(createError(`Unknown engine command: ${String(command)}`)))
    process.exitCode = 1
  } catch (error) {
    const message = error instanceof Error
      ? error.message
      : String(error)

    process.stdout.write(JSON.stringify(createError(message)))
    process.exitCode = 1
  }
}

main()
