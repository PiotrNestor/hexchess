<template>
  <div>
    <Input
      v-model="fen"
      name="fen"
      select-all />

    <div class="flex flex-wrap items-center gap-x-6 gap-y-2 mt-4">
      <label class="flex items-center gap-x-2 text-sm tracking-wide">
        Engine

        <select
          v-model="engineKind"
          class="border rounded-md px-2 py-1 bg-transparent"
        >
          <option value="rust-worker">Rust (WASM Worker)</option>
          <option value="python-api">Pythonic (FastAPI)</option>
          <option value="cyengine-api">Cython (FastAPI)</option>
        </select>
      </label>

      <label class="flex items-center gap-x-2 text-sm tracking-wide">
        Match White

        <select
          v-model="matchWhiteEngine"
          class="border rounded-md px-2 py-1 bg-transparent"
        >
          <option value="rust-worker">Rust</option>
          <option value="python-api">Pythonic</option>
          <option value="cyengine-api">Cython</option>
        </select>
      </label>

      <div
        v-if="engineKind === 'python-api' || engineKind === 'cyengine-api'"
        class="text-xs tracking-wide opacity-75"
      >
          API-backed engines are slower than the in-browser Rust worker at higher depths.
      </div>

      <button
        class="flex gap-x-1.5 items-center text-sm tracking-wide hover:text-(--vp-code-color)!"
        @click="onResetClick">
        <svg class="size-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
        
        Reset
      </button>

      <button
        class="flex gap-x-1.5 items-center text-sm tracking-wide hover:text-(--vp-code-color)!"
        @click="onClearClick">
        <svg class="size-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 21H8a2 2 0 0 1-1.42-.587l-3.994-3.999a2 2 0 0 1 0-2.828l10-10a2 2 0 0 1 2.829 0l5.999 6a2 2 0 0 1 0 2.828L12.834 21"/><path d="m5.082 11.09 8.828 8.828"/></svg>
      
        Clear
      </button>

      <button
        class="flex gap-x-1.5 items-center text-sm tracking-wide hover:text-(--vp-code-color)!"
        @click="onFlipClick">
        <svg class="size-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21 16-4 4-4-4"/><path d="M17 20V4"/><path d="m3 8 4-4 4 4"/><path d="M7 4v16"/></svg>
      
        Flip
      </button>

      <button
        class="flex gap-x-1.5 items-center text-sm tracking-wide hover:text-(--vp-code-color)!"
        @click="onSaveGameClick">
        <svg class="size-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/></svg>

        Save Moves
      </button>

      <button
        class="flex gap-x-1.5 items-center text-sm tracking-wide hover:text-(--vp-code-color)!"
        @click="onLoadGameClick">
        <svg class="size-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21V9"/><path d="m17 14-5-5-5 5"/><path d="M19 3H5"/></svg>

        Load Moves
      </button>

      <button
        :class="[
          'flex gap-x-1.5 items-center text-sm tracking-wide hover:text-(--vp-code-color)!',
          loading && 'opacity-50 pointer-events-none',
        ]"
        :disabled="loading"
        @click="onPlayClick">
        <Spinner
          v-if="loading"
          class="size-4" />
          
        <svg
          v-else
          class="size-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20v2"/><path d="M12 2v2"/><path d="M17 20v2"/><path d="M17 2v2"/><path d="M2 12h2"/><path d="M2 17h2"/><path d="M2 7h2"/><path d="M20 12h2"/><path d="M20 17h2"/><path d="M20 7h2"/><path d="M7 20v2"/><path d="M7 2v2"/><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="8" y="8" width="8" height="8" rx="1"/></svg>
        
        Play
      </button>

      <button
        :class="[
          'flex gap-x-1.5 items-center text-sm tracking-wide hover:text-(--vp-code-color)!',
          loading && !matchRunning && 'opacity-50 pointer-events-none',
        ]"
        :disabled="loading && !matchRunning"
        @click="onMatchClick">
        <Spinner
          v-if="loading && matchRunning"
          class="size-4" />

        <svg
          v-else
          class="size-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/></svg>

        {{ matchRunning ? 'Stop Match' : 'Engine Match' }}
      </button>
    </div>
      <input
        ref="gameFileInput"
        type="file"
        accept=".yaml,.yml,text/yaml,application/yaml"
        class="hidden"
        @change="onGameFileChange">


    <div class="mt-2 text-xs tracking-wide opacity-75">
      Match pairing: White {{ engineLabel(matchWhiteEngine) }}, Black {{ engineLabel(matchBlackEngine) }}.
    </div>

    <div class="mt-3">
      <EvaluationResult
        v-model:depth="depth"
        :evaluation="evaluation" />
    </div>

    <Hexboard
      v-model:selected="selected"
      active
      autoselect
      ignore-turn
      :flipped="flipped"
      :hexchess="hexchess"
      :highlight="highlight"
      :playing="true"
      @move="onMove"
      @click-position="onClickPosition">
      <template #promotion="{ b, cancel,  n, promote, q, r }">
        <div
          class="absolute bottom-full flex flex-row left-1/2 shadow-lg rounded-lg -translate-x-1/2 dark:bg-gray-700"
        >
          <PromotionPiece :piece="n" @click="promote('n')" />
          <PromotionPiece :piece="b" @click="promote('b')" />
          <PromotionPiece :piece="q" @click="promote('q')" />
          <PromotionPiece :piece="r" @click="promote('r')" />
          <button
            @click="cancel"
            class="cursor-pointer flex items-center justify-center h-14 rounded-r-lg w-14 dark:hover:bg-gray-600!">
            <X class="size-8" />
          </button>
        </div>
      </template>
    </Hexboard>

    <div class="mt-4 rounded-lg border p-3">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="text-sm tracking-wide">
          Move history: {{ moveHistory.length }}
          <span class="opacity-70">
            {{ currentMoveLabel }}
          </span>
        </div>

        <div class="flex items-center gap-2 text-sm tracking-wide">
          <button
            class="rounded border px-2 py-1 hover:text-(--vp-code-color)! disabled:opacity-40"
            :disabled="historyIndex === 0"
            @click="jumpToStart">
            |&lt;
          </button>

          <button
            class="rounded border px-2 py-1 hover:text-(--vp-code-color)! disabled:opacity-40"
            :disabled="historyIndex === 0"
            @click="stepBackward">
            &lt;
          </button>

          <button
            class="rounded border px-2 py-1 hover:text-(--vp-code-color)! disabled:opacity-40"
            :disabled="historyIndex >= moveHistory.length"
            @click="stepForward">
            &gt;
          </button>

          <button
            class="rounded border px-2 py-1 hover:text-(--vp-code-color)! disabled:opacity-40"
            :disabled="historyIndex >= moveHistory.length"
            @click="jumpToLatest">
            &gt;|
          </button>
        </div>
      </div>

      <div
        v-if="groupedMoves.length > 0"
        class="mt-3 max-h-48 overflow-y-auto rounded-md border px-2 py-1 text-sm"
      >
        <div
          v-for="row in groupedMoves"
          :key="row.number"
          class="grid grid-cols-[3rem_1fr_1fr] items-center gap-2 py-1"
        >
          <div class="opacity-70">
            {{ row.number }}.
          </div>

          <button
            v-if="row.white"
            :class="[
              'rounded px-2 py-1 text-left hover:text-(--vp-code-color)!',
              historyIndex === row.white.index && 'bg-(--vp-c-bg-soft)',
            ]"
            @click="jumpToHistory(row.white.index)">
            <span v-if="moveSourceLabel(row.white.source)" class="opacity-70">[{{ moveSourceLabel(row.white.source) }}]</span> {{ row.white.san }}<span v-if="row.white.evaluations !== null || row.white.duration !== null" class="opacity-70"> ({{ row.white.evaluations?.toLocaleString() ?? 0 }} evals, {{ row.white.duration?.toFixed(0) ?? 0 }}ms)</span>
          </button>
          <div v-else />

          <button
            v-if="row.black"
            :class="[
              'rounded px-2 py-1 text-left hover:text-(--vp-code-color)!',
              historyIndex === row.black.index && 'bg-(--vp-c-bg-soft)',
            ]"
            @click="jumpToHistory(row.black.index)">
            <span v-if="moveSourceLabel(row.black.source)" class="opacity-70">[{{ moveSourceLabel(row.black.source) }}]</span> {{ row.black.san }}<span v-if="row.black.evaluations !== null || row.black.duration !== null" class="opacity-70"> ({{ row.black.evaluations?.toLocaleString() ?? 0 }} evals, {{ row.black.duration?.toFixed(0) ?? 0 }}ms)</span>
          </button>
          <div v-else />
        </div>
      </div>

      <div
        v-else
        class="mt-3 text-sm opacity-70"
      >
        No moves recorded yet.
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue'
import { parse as parseYaml, stringify as stringifyYaml } from 'yaml'
import { Hexboard } from '@bedard/hexboard'
import { Hexchess, San } from '../../js/src'
import { useEngine, type EngineKind, type SearchResult } from './use-engine'
import { useEventListener } from '@vueuse/core'
// @ts-ignore Vue SFC default export is provided by Vue tooling
import EvaluationResult from './EvaluationResult.vue'
// @ts-ignore Vue SFC default export is provided by Vue tooling
import Input from '../components/Input.vue'
// @ts-ignore Vue SFC default export is provided by Vue tooling
import PromotionPiece from '../components/PromotionPiece.vue'
// @ts-ignore Vue SFC default export is provided by Vue tooling
import Spinner from '../components/Spinner.vue'
// @ts-ignore Vue SFC default export is provided by Vue tooling
import X from '../components/icons/X.vue'

type MoveSource = EngineKind | 'manual'

interface SavedGameMove {
  san: string
  source?: MoveSource | null
  evaluations?: number | null
  duration?: number | null
}

interface SavedGameFile {
  version: 1
  startFen: string
  historyIndex: number
  moves: SavedGameMove[]
}

interface RestoreHistoryResult {
  invalidMove: {
    index: number
    san: string
    message: string
  } | null
  loadedMoves: number
}

const { engineKind, evaluate, evaluateWith, loading } = useEngine()

//
// state
//

const depth = ref(3)

const flipped = ref(false)

const highlight = ref<number[]>([])

const hexchess = ref(Hexchess.init())

const selected = ref<number | null>(null)

const evaluation = ref<SearchResult | null>(null)

const gameFileInput = ref<HTMLInputElement | null>(null)

const matchRunning = ref(false)

const matchWhiteEngine = ref<EngineKind>('rust-worker')

const historyStartFen = ref(Hexchess.init().toString())

const historyIndex = ref(0)

const moveHistory = ref<Array<{
  san: string
  from: number
  to: number
  beforeFen: string
  afterFen: string
  source: MoveSource | null
  evaluations: number | null
  duration: number | null
}>>([])

let matchToken = 0

//
// computed
//

const fen = computed({
  get: () => hexchess.value.toString(),
  set: (value) => {
    if (value) {
      try {
        const next = Hexchess.parse(value)
        replacePosition(next)
      } catch { }
    }
  }
})

const matchBlackEngine = computed<EngineKind>(() => {
  if (matchWhiteEngine.value === 'rust-worker') {
    return engineKind.value === 'rust-worker' ? 'python-api' : engineKind.value
  }

  return 'rust-worker'
})

const groupedMoves = computed(() => {
  const start = Hexchess.parse(historyStartFen.value)
  const result: Array<{
    number: number
    white: { index: number, san: string, source: MoveSource | null, evaluations: number | null, duration: number | null } | null
    black: { index: number, san: string, source: MoveSource | null, evaluations: number | null, duration: number | null } | null
  }> = []

  let nextTurn: 'w' | 'b' = start.turn
  let moveNumber = start.fullmove
  let currentRow: {
    number: number
    white: { index: number, san: string, source: MoveSource | null, evaluations: number | null, duration: number | null } | null
    black: { index: number, san: string, source: MoveSource | null, evaluations: number | null, duration: number | null } | null
  } | null = null

  for (let i = 0; i < moveHistory.value.length; i += 1) {
    const entry = {
      index: i + 1,
      san: moveHistory.value[i].san,
      source: moveHistory.value[i].source,
      evaluations: moveHistory.value[i].evaluations,
      duration: moveHistory.value[i].duration,
    }

    if (currentRow === null || currentRow.number !== moveNumber) {
      currentRow = {
        number: moveNumber,
        white: null,
        black: null,
      }
      result.push(currentRow)
    }

    if (nextTurn === 'w') {
      currentRow.white = entry
      nextTurn = 'b'
    } else {
      currentRow.black = entry
      nextTurn = 'w'
      moveNumber += 1
      currentRow = null
    }
  }

  return result
})

const currentMoveLabel = computed(() => {
  if (historyIndex.value === 0) {
    return '(start position)'
  }

  const current = moveHistory.value[historyIndex.value - 1]

  return current ? `(showing ${current.san})` : '(latest position)'
})

//
// lifecycle
//

onMounted(() => {
  useEventListener(window, 'keydown', (evt) => {
    if (evt.key === 'Escape') {
      deselect()
    } else if ((evt.key === 'Delete' || evt.key === 'Backspace') && selected.value !== null) {
      hexchess.value.board[selected.value] = null
      deselect()
    } else if (selected.value !== null && 'pbnrqkPBNRQK'.includes(evt.key)) {
      evt.preventDefault()
      hexchess.value.board[selected.value] = evt.key as any
    }
  })
})

//
// methods
//

function deselect() {
  highlight.value = []
  selected.value = null
}

function replacePosition(next: Hexchess) {
  hexchess.value = next
  historyStartFen.value = next.toString()
  historyIndex.value = 0
  moveHistory.value = []
  highlight.value = []
}

function restoreHistory(startFen: string, moves: SavedGameMove[], nextHistoryIndex: number): RestoreHistoryResult {
  let current = Hexchess.parse(startFen)
  const nextHistory: typeof moveHistory.value = []
  let invalidMove: RestoreHistoryResult['invalidMove'] = null

  for (let index = 0; index < moves.length; index += 1) {
    const move = moves[index]

    try {
      const san = San.from(move.san)
      const beforeFen = current.toString()
      const next = current.clone()

      next.applyMove(san)
      current = next

      nextHistory.push({
        san: san.toString(),
        from: san.from,
        to: san.to,
        beforeFen,
        afterFen: next.toString(),
        source: move.source ?? null,
        evaluations: move.evaluations ?? null,
        duration: move.duration ?? null,
      })
    } catch (err) {
      invalidMove = {
        index: index + 1,
        san: move.san,
        message: err instanceof Error ? err.message : String(err),
      }
      break
    }
  }

  const boundedIndex = Math.max(0, Math.min(nextHistoryIndex, nextHistory.length))
  const entry = boundedIndex > 0 ? nextHistory[boundedIndex - 1] : null

  stopMatch()
  evaluation.value = null
  historyStartFen.value = startFen
  moveHistory.value = nextHistory
  historyIndex.value = boundedIndex
  hexchess.value = Hexchess.parse(entry?.afterFen ?? startFen)
  highlight.value = entry ? [entry.from, entry.to] : []
  selected.value = null

  return {
    invalidMove,
    loadedMoves: nextHistory.length,
  }
}

function saveTextFile(fileName: string, content: string) {
  const blob = new Blob([content], { type: 'text/yaml' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')

  link.href = url
  link.download = fileName
  link.click()

  URL.revokeObjectURL(url)
}

function formatExportTimestamp() {
  const now = new Date()
  const pad = (value: number) => value.toString().padStart(2, '0')

  return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`
}

function applyMoveToHistory(san: San, meta: { source?: MoveSource | null, evaluations?: number | null, duration?: number | null } = {}) {
  const current = hexchess.value.clone()
  const beforeFen = current.toString()
  const next = current.clone()

  next.applyMove(san)

  if (historyIndex.value < moveHistory.value.length) {
    moveHistory.value = moveHistory.value.slice(0, historyIndex.value)
  }

  moveHistory.value = [
    ...moveHistory.value,
    {
      san: san.toString(),
      from: san.from,
      to: san.to,
      beforeFen,
      afterFen: next.toString(),
      source: meta.source ?? null,
      evaluations: meta.evaluations ?? null,
      duration: meta.duration ?? null,
    },
  ]

  historyIndex.value = moveHistory.value.length
  hexchess.value = next
  highlight.value = [san.from, san.to]
}

function jumpToHistory(index: number) {
  const bounded = Math.max(0, Math.min(index, moveHistory.value.length))
  const entry = bounded > 0 ? moveHistory.value[bounded - 1] : null
  const fen = entry?.afterFen ?? historyStartFen.value

  stopMatch()
  evaluation.value = null
  hexchess.value = Hexchess.parse(fen)
  historyIndex.value = bounded
  highlight.value = entry ? [entry.from, entry.to] : []
  selected.value = null
}

function jumpToStart() {
  jumpToHistory(0)
}

function jumpToLatest() {
  jumpToHistory(moveHistory.value.length)
}

function stepBackward() {
  jumpToHistory(historyIndex.value - 1)
}

function stepForward() {
  jumpToHistory(historyIndex.value + 1)
}

function engineForTurn(turn: 'w' | 'b'): EngineKind {
  return turn === 'w' ? matchWhiteEngine.value : matchBlackEngine.value
}

function engineLabel(kind: EngineKind) {
  if (kind === 'python-api') {
    return 'Pythonic'
  }

  if (kind === 'cyengine-api') {
    return 'Cython'
  }

  return 'Rust'
}

function moveSourceLabel(source: MoveSource | null | undefined) {
  if (source === 'python-api') {
    return 'Py'
  }

  if (source === 'cyengine-api') {
    return 'Cy'
  }

  if (source === 'rust-worker') {
    return 'Rust'
  }

  if (source === 'manual') {
    return 'Manual'
  }

  return null
}

function stopMatch() {
  matchRunning.value = false
  matchToken += 1
}

function onClearClick() {
  stopMatch()
  evaluation.value = null
  replacePosition(new Hexchess())
}

function onFlipClick() {
  flipped.value = !flipped.value
}

function reportIllegalEngineMove(kind: EngineKind, san: San) {
  const message = `${engineLabel(kind)} engine returned illegal move ${san.toString()} for position ${hexchess.value.toString()}`

  console.error('[hexchess-sandbox] illegal engine move', {
    kind,
    move: san.toString(),
    position: hexchess.value.toString(),
  })

  window.alert(message)
}

function onSaveGameClick() {
  const payload: SavedGameFile = {
    version: 1,
    startFen: historyStartFen.value,
    historyIndex: historyIndex.value,
    moves: moveHistory.value.map((move) => ({
      san: move.san,
      source: move.source,
      evaluations: move.evaluations,
      duration: move.duration,
    })),
  }

  saveTextFile(`hexchess-game-${formatExportTimestamp()}.yaml`, stringifyYaml(payload))
}

function onLoadGameClick() {
  gameFileInput.value?.click()
}

async function onGameFileChange(evt: Event) {
  const input = evt.target as HTMLInputElement | null
  const file = input?.files?.[0]

  if (!file) {
    return
  }

  try {
    const raw = await file.text()
    const parsed = parseYaml(raw) as Partial<SavedGameFile>

    if (parsed.version !== 1 || typeof parsed.startFen !== 'string' || !Array.isArray(parsed.moves)) {
      throw new Error('Invalid game file format')
    }

    const result = restoreHistory(
      parsed.startFen,
      parsed.moves,
      typeof parsed.historyIndex === 'number' ? parsed.historyIndex : parsed.moves.length,
    )

    if (result.invalidMove) {
      console.warn('[hexchess-sandbox] loaded partial game history', result)
      window.alert(
        `Loaded ${result.loadedMoves} moves. Stopped at invalid saved move ${result.invalidMove.index} (${result.invalidMove.san}).`,
      )
    }
  } catch (err) {
    console.error('[hexchess-sandbox] failed to load moves', err)
    window.alert('Failed to load game moves file.')
  } finally {
    if (input) {
      input.value = ''
    }
  }
}

function onMove(san: San) {
  stopMatch()
  evaluation.value = null
  applyMoveToHistory(san, { source: 'manual' })
}

async function onPlayClick() {
  const kind = engineKind.value
  const data = await evaluate({
    depth: depth.value,
    position: hexchess.value.toString(),
  })

  if (!data) {
    return
  }

  evaluation.value = data?.response
  
  if (data.response.sans.length > 0) {
    const best = data.response.sans[0]
    const san = San.from(best.san)

    try {
      applyMoveToHistory(san, {
        source: kind,
        evaluations: data.response.evaluations,
        duration: data.response.duration,
      })
    } catch {
      reportIllegalEngineMove(kind, san)
      return
    }
  }
}

function onClickPosition(position: number) {
  selected.value = position
}

function onResetClick() {
  stopMatch()
  evaluation.value = null
  replacePosition(Hexchess.init())
}

async function playBestMove(kind: EngineKind) {
  const data = await evaluateWith(kind, {
    depth: depth.value,
    position: hexchess.value.toString(),
  })

  if (!data) {
    return false
  }

  evaluation.value = data.response

  if (data.response.sans.length === 0) {
    return false
  }

  const best = data.response.sans[0]
  const san = San.from(best.san)

  try {
    applyMoveToHistory(san, {
      source: kind,
      evaluations: data.response.evaluations,
      duration: data.response.duration,
    })
    return true
  } catch {
    reportIllegalEngineMove(kind, san)
    return false
  }
}

async function onMatchClick() {
  if (matchRunning.value) {
    stopMatch()
    return
  }

  const token = ++matchToken
  matchRunning.value = true

  try {
    for (let ply = 0; ply < 400; ply += 1) {
      if (token !== matchToken) {
        return
      }

      const current = hexchess.value

      if (current.isCheckmate() || current.isStalemate()) {
        return
      }

      const moved = await playBestMove(engineForTurn(current.turn))

      if (!moved) {
        return
      }
    }
  } finally {
    if (token === matchToken) {
      matchRunning.value = false
    }
  }
}
</script>
