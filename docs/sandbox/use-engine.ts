import { onUnmounted, ref } from 'vue'
import {
  evaluate as evaluateCommand,
  ping as pingCommand,
  type EvaluateOptions,
  type EvaluateResponse,
  type ExecuteResponse,
  type SearchMetrics,
} from '../../engine/index'

export type { SearchMetrics }

export interface SearchResult extends EvaluateResponse {
  duration: number
}

const DEBUG_ENGINE = true

function log(...args: unknown[]) {
  if (DEBUG_ENGINE) {
    console.info('[hexchess-engine]', ...args)
  }
}

export type EngineKind = 'rust-worker' | 'python-api' | 'cyengine-api'

const ENGINE_MAX_DEPTH: Record<EngineKind, number | null> = {
  'rust-worker': 4,
  'python-api': null,
  'cyengine-api': null,
}

export function getEngineMaxDepth(kind: EngineKind) {
  return ENGINE_MAX_DEPTH[kind]
}

export function clampDepthForEngine(kind: EngineKind, depth: number) {
  const normalizedDepth = Math.max(1, depth)
  const maxDepth = getEngineMaxDepth(kind)

  return maxDepth === null ? normalizedDepth : Math.min(normalizedDepth, maxDepth)
}

const PYENGINE_BASE_URL = 'http://127.0.0.1:8000'
const CYENGINE_BASE_URL = 'http://127.0.0.1:8001'

function timeoutMsFor(kind: EngineKind, options: EvaluateOptions) {
  if (kind !== 'rust-worker') {
    return 120000
  }

  const depth = Math.max(1, options.depth)
  return Math.max(120000, depth * 120000)
}

export function useEngine() {
  let worker: Worker | null = null

  const engineKind = ref<EngineKind>('rust-worker')
  const pendingRequests = ref(0)

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

  const resetWorker = () => {
    worker?.terminate()
    worker = null
  }

  const executeApiEngine = async (
    baseUrl: string,
    engineName: string,
    command: string,
    options: EvaluateOptions | Record<string, unknown>,
  ) => {
    const response = await fetch(`${baseUrl}/execute`, {
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
      throw new Error(`${engineName} request failed (${response.status}): ${body}`)
    }

    return response.json() as Promise<ExecuteResponse<EvaluateResponse>>
  }

  const loading = ref(false)

  const setLoading = (delta: 1 | -1) => {
    pendingRequests.value = Math.max(0, pendingRequests.value + delta)
    loading.value = pendingRequests.value > 0
  }

  const evaluateWith = async (kind: EngineKind, options: EvaluateOptions) => {
    setLoading(1)

    try {
      log('evaluate:start', { kind, ...options })
      const startedAt = performance.now()

      let result: ExecuteResponse<EvaluateResponse>

      if (kind === 'python-api') {
        result = await executeApiEngine(PYENGINE_BASE_URL, 'Pythonic engine', 'hexchess/evaluate', options)
      } else if (kind === 'cyengine-api') {
        result = await executeApiEngine(CYENGINE_BASE_URL, 'Cython engine', 'hexchess/evaluate', options)
      } else {
        const currentWorker = ensureWorker()

        if (!currentWorker) {
          setLoading(-1)
          return
        }

        result = await evaluateCommand(currentWorker, options, {
          timeoutMs: timeoutMsFor(kind, options),
        })
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

      return {
        ...result,
        response,
      } as ExecuteResponse<SearchResult>
    } catch (err) {
      if (kind === 'rust-worker' && err instanceof Error && err.message.includes('timed out after')) {
        resetWorker()
      }
      console.error('[hexchess-engine] evaluate failed', err)
    } finally {
      setLoading(-1)
    }
  }

  const evaluate = async (options: EvaluateOptions) => evaluateWith(engineKind.value, options)

  onUnmounted(() => {
    resetWorker()
  })

  return {
    engineKind,
    evaluate,
    evaluateWith,
    loading,
  }
}