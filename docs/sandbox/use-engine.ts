import { onUnmounted, ref } from 'vue'
import {
  evaluate as evaluateCommand,
  ping as pingCommand,
  type EvaluateOptions,
  type EvaluateResponse,
  type ExecuteResponse,
} from '../../engine/index'

export interface SearchResult extends EvaluateResponse {
  duration: number
}

const DEBUG_ENGINE = true

function log(...args: unknown[]) {
  if (DEBUG_ENGINE) {
    console.info('[hexchess-engine]', ...args)
  }
}

export type EngineKind = 'rust-worker' | 'python-api'

const PYENGINE_BASE_URL = 'http://127.0.0.1:8000'

export function useEngine() {
  let worker: Worker | null = null

  const engineKind = ref<EngineKind>('rust-worker')

  const ensureWorker = () => {
    if (worker || typeof window === 'undefined' || typeof Worker === 'undefined') {
      return worker
    }

    log('creating worker', '/engine/worker.js')
    worker = new Worker('/engine/worker.js', { type: 'module' })

    worker.addEventListener('error', (evt) => {
      console.error('[hexchess-engine] worker error', evt)
    })

    worker.addEventListener('messageerror', (evt) => {
      console.error('[hexchess-engine] worker messageerror', evt)
    })

    pingCommand(worker)
      .then((result) => {
        log('ping ok', result.response)
      })
      .catch((err) => {
        console.error('[hexchess-engine] ping failed', err)
      })

    return worker
  }

  const executePython = async (command: string, options: EvaluateOptions | Record<string, unknown>) => {
    const response = await fetch(`${PYENGINE_BASE_URL}/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        command,
        options,
      }),
    })

    if (!response.ok) {
      const body = await response.text()
      throw new Error(`Python engine request failed (${response.status}): ${body}`)
    }

    return response.json() as Promise<ExecuteResponse<EvaluateResponse>>
  }

  const loading = ref(false)

  const evaluate = async (options: EvaluateOptions) => {
    if (loading.value) {
      return
    }

    loading.value = true

    try {
      log('evaluate:start', options)
      const startedAt = performance.now()

      let result: ExecuteResponse<EvaluateResponse>

      if (engineKind.value === 'python-api') {
        result = await executePython('hexchess/evaluate', options)
      } else {
        const currentWorker = ensureWorker()

        if (!currentWorker) {
          loading.value = false
          return
        }

        result = await evaluateCommand(currentWorker, options)
      }

      const duration = performance.now() - startedAt
      log('evaluate:done', {
        depth: result.response.depth,
        evaluations: result.response.evaluations,
        duration,
      })

      const response: SearchResult = {
        ...result.response,
        duration,
      }

      loading.value = false
      return {
        ...result,
        response,
      } as ExecuteResponse<SearchResult>
    } catch (err) {
      console.error('[hexchess-engine] evaluate failed', err)
      loading.value = false
    }
  }

  onUnmounted(() => {
    worker?.terminate()
    worker = null
  })

  return {
    engineKind,
    evaluate,
    loading,
  }
}