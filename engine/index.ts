export interface EvaluateOptions {
  depth: number
  position: string
}

export interface EvaluateResponse {
  depth: number
  evaluations: number
  sans: { san: string, score: number }[]
}

export interface PingResponse {
  now: number
}

export interface ExecuteResponse<T extends Record<string, any> = {}> {
  command: string
  options: Record<string, unknown>
  response: T
}

/** execute a command with the engine worker */
export function execute<T extends Record<string, any> = {}>(
  worker: Worker,
  command: string,
  options: Record<string, any> = {},
  timeoutMs = 120000,
) {
  const id = crypto.randomUUID()

  return new Promise<ExecuteResponse<T>>((resolve, reject) => {
    const cleanup = (
      messageListener: (evt: MessageEvent) => void,
      errorListener: (evt: ErrorEvent) => void,
      messageErrorListener: (evt: MessageEvent) => void,
      timeoutId: ReturnType<typeof setTimeout>,
    ) => {
      clearTimeout(timeoutId)
      worker.removeEventListener('message', messageListener)
      worker.removeEventListener('error', errorListener)
      worker.removeEventListener('messageerror', messageErrorListener)
    }

    const messageListener = (evt: MessageEvent) => {
      if (evt.data?.id !== id) {
        return
      }

      cleanup(messageListener, errorListener, messageErrorListener, timeoutId)

      if (evt.data?.error) {
        const error = evt.data.error
        const message = typeof error?.message === 'string'
          ? error.message
          : `Engine command failed: ${command}`

        reject(new Error(message))
        return
      }

      resolve({
        command,
        options: evt.data.options ?? options,
        response: (evt.data.response ?? {}) as T,
      })
    }

    const errorListener = (evt: ErrorEvent) => {
      cleanup(messageListener, errorListener, messageErrorListener, timeoutId)
      reject(new Error(`Engine worker error while running ${command}: ${evt.message || 'unknown error'}`))
    }

    const messageErrorListener = () => {
      cleanup(messageListener, errorListener, messageErrorListener, timeoutId)
      reject(new Error(`Engine worker message error while running ${command}`))
    }

    const timeoutId = setTimeout(() => {
      cleanup(messageListener, errorListener, messageErrorListener, timeoutId)
      reject(new Error(`Engine command timed out after ${timeoutMs}ms: ${command}`))
    }, timeoutMs)

    worker.addEventListener('message', messageListener)
    worker.addEventListener('error', errorListener)
    worker.addEventListener('messageerror', messageErrorListener)

    try {
      worker.postMessage({ command, id, options })
    } catch (err) {
      cleanup(messageListener, errorListener, messageErrorListener, timeoutId)
      reject(err)
    }
  });
}

/** evaluate a position */
export function evaluate(worker: Worker, options: EvaluateOptions) {
  return execute<EvaluateResponse>(worker, 'hexchess/evaluate', options)
}

/** test for a connection with the engine worker */
export function ping(worker: Worker) {
  return execute<PingResponse>(worker, 'hexchess/ping')
}