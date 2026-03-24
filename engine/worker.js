import * as engine from './pkg/hexchess_engine.js'

const ready = engine.default()
  .then(() => {
    console.info('[hexchess-engine-worker] wasm initialized')
  })
  .catch((error) => {
    console.error('[hexchess-engine-worker] wasm init failed', error)
    throw error
  })

onmessage = async evt => {
  const { command, id, options } = evt.data

  if (typeof command === 'string' && typeof id === 'string') {
    const post = (response = {}) => postMessage({ id, response, options })
    const postError = (error) => postMessage({
      id,
      options,
      error: {
        message: error instanceof Error
          ? error.message
          : String(error),
      },
    })

    console.info('[hexchess-engine-worker] command', command, options)

    try {
      await ready

      switch (command) {
        case 'hexchess/evaluate':
          post(engine.evaluate(options))
          break
        case 'hexchess/ping':
          post({ now: Date.now() })
          break
        default:
          postError(`Unknown engine command: ${command}`)
          break
      }
    } catch (error) {
      console.error('[hexchess-engine-worker] command failed', command, error)
      postError(error)
    }
  }
}
