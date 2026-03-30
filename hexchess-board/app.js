import './vendor/hexchess-board/hexchess-board.js'
import { Hexchess, San, positions } from './vendor/hexchess/index.mjs'
import YAML from './vendor/yaml/browser/index.js'

const BOARD_COLUMNS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'K', 'L']

function rowsForColumn(column) {
  switch (column) {
    case 'A':
    case 'L':
      return 6
    case 'B':
    case 'K':
      return 7
    case 'C':
    case 'I':
      return 8
    case 'D':
    case 'H':
      return 9
    case 'E':
    case 'G':
      return 10
    case 'F':
      return 11
    default:
      throw new Error(`Unsupported column: ${column}`)
  }
}

function compressFenColumn(source) {
  let result = ''
  let blanks = 0

  for (const char of source) {
    if (char === '1') {
      blanks += 1
    } else {
      if (blanks > 0) {
        result += String(blanks)
        blanks = 0
      }
      result += char
    }
  }

  if (blanks > 0) {
    result += String(blanks)
  }

  return result || '1'
}

function squareNameFromPosition(positionName) {
  const column = positionName[0].toUpperCase()
  const row = positionName.slice(1)
  return `${column}${row}`
}

function toBoardComponentFen(game) {
  const squareToPiece = Object.create(null)

  for (let i = 0; i < positions.length; i += 1) {
    const piece = game.board[i]
    if (!piece) {
      continue
    }

    squareToPiece[squareNameFromPosition(positions[i])] = piece
  }

  const columns = []
  for (const column of BOARD_COLUMNS) {
    const rows = rowsForColumn(column)
    let raw = ''

    for (let row = 1; row <= rows; row += 1) {
      const square = `${column}${row}`
      raw += squareToPiece[square] || '1'
    }

    columns.push(compressFenColumn(raw))
  }

  return columns.join('/')
}

const boardEl = document.getElementById('board')
const engineUrlEl = document.getElementById('engine-url')
const engineDepthEl = document.getElementById('engine-depth')
const whiteSideEl = document.getElementById('white-side')
const blackSideEl = document.getElementById('black-side')
const statusEl = document.getElementById('status')
const historyEl = document.getElementById('history')
const historySummaryEl = document.getElementById('history-summary')
const loadInputEl = document.getElementById('load-input')

const pingBtn = document.getElementById('ping')
const playEngineBtn = document.getElementById('play-engine')
const toggleMatchBtn = document.getElementById('toggle-match')
const flipBtn = document.getElementById('flip')
const flipTopPiecesBtn = document.getElementById('flip-top-pieces')
const resetBtn = document.getElementById('reset')
const saveBtn = document.getElementById('save')
const loadBtn = document.getElementById('load')
const navStartBtn = document.getElementById('nav-start')
const navBackBtn = document.getElementById('nav-back')
const navForwardBtn = document.getElementById('nav-forward')
const navEndBtn = document.getElementById('nav-end')

const START_FEN = Hexchess.init().toString()
const ENGINE_TYPES = ['pyengine2', 'pyrustengine']
const DEFAULT_LOCAL_ENGINE_URLS = {
  pyengine2: 'http://127.0.0.1:8000',
  pyrustengine: 'http://127.0.0.1:8081',
}
const ENGINE_URL_STORAGE_KEY = 'hexchess-board.engine-url'

let startFen = START_FEN
let moveHistory = []
let historyIndex = 0
let evaluation = null
let currentGame = Hexchess.parse(startFen)
let matchToken = 0
let isBusy = false
let suppressBoardMoveEvent = false
let flipTopPiecesEnabled = false

function updatePieceRotationMode() {
  boardEl.rotateTopPieces = flipTopPiecesEnabled
  boardEl.rotateBlackPieces = flipTopPiecesEnabled
  if (typeof boardEl.requestUpdate === 'function') {
    boardEl.requestUpdate('rotateTopPieces')
  }
  if (typeof boardEl.resize === 'function') {
    boardEl.resize()
  }
  if (flipTopPiecesBtn) {
    flipTopPiecesBtn.textContent = `Flip Top Pieces: ${flipTopPiecesEnabled ? 'On' : 'Off'}`
  }
}

function toggleBlackPieceRotationMode() {
  flipTopPiecesEnabled = !flipTopPiecesEnabled
  updatePieceRotationMode()
}

function setStatus(message, isError = false) {
  statusEl.textContent = message
  if (isError) {
    statusEl.style.background = '#fde8e8'
    statusEl.style.borderColor = '#f7b6b6'
    statusEl.style.color = '#6a1212'
  } else {
    statusEl.style.background = '#d5ece7'
    statusEl.style.borderColor = '#bddcd4'
    statusEl.style.color = '#0d453c'
  }
}

function sanitizeEngineUrl(raw) {
  return raw.trim().replace(/\/$/, '')
}

function isEngineType(value) {
  return ENGINE_TYPES.includes(value)
}

function getSideValue(turn) {
  return turn === 'w' ? whiteSideEl.value : blackSideEl.value
}

function getTurnEngineType(turn) {
  const value = getSideValue(turn)
  return isEngineType(value) ? value : null
}

function isEngineMoveSource(value) {
  return isEngineType(value)
}

function getRuntimeGlobalEngineUrl() {
  const configured = window?.HEXCHESS_CONFIG?.engineUrl
  if (typeof configured !== 'string') {
    return null
  }

  const sanitized = sanitizeEngineUrl(configured)
  return sanitized.length > 0 ? sanitized : null
}

function getRuntimeEngineUrl(engineType) {
  const engineUrls = window?.HEXCHESS_CONFIG?.engineUrls
  if (engineUrls && typeof engineUrls === 'object') {
    const configured = engineUrls[engineType]
    if (typeof configured === 'string') {
      const sanitized = sanitizeEngineUrl(configured)
      if (sanitized.length > 0) {
        return sanitized
      }
    }
  }

  return getRuntimeGlobalEngineUrl()
}

function getStoredEngineUrl() {
  try {
    const stored = localStorage.getItem(ENGINE_URL_STORAGE_KEY)
    if (!stored) {
      return null
    }

    const sanitized = sanitizeEngineUrl(stored)
    return sanitized.length > 0 ? sanitized : null
  } catch {
    return null
  }
}

function isGitHubPagesHost() {
  return typeof window !== 'undefined' && window.location.hostname.endsWith('github.io')
}

function resolveInitialEngineUrl() {
  const runtime = getRuntimeGlobalEngineUrl()
  if (runtime) {
    return runtime
  }

  const stored = getStoredEngineUrl()
  if (stored) {
    return stored
  }

  return ''
}

function persistEngineUrl(value) {
  try {
    const sanitized = sanitizeEngineUrl(value)
    if (sanitized.length === 0) {
      localStorage.removeItem(ENGINE_URL_STORAGE_KEY)
      return
    }

    localStorage.setItem(ENGINE_URL_STORAGE_KEY, sanitized)
  } catch {
    // Ignore storage errors in restricted environments.
  }
}

function getEngineDepth() {
  const depth = Number(engineDepthEl.value)
  if (!Number.isInteger(depth) || depth < 1) {
    return 1
  }

  return Math.min(depth, 8)
}

function sideIsEngine(turn) {
  return getTurnEngineType(turn) !== null
}

function getPreferredEngineType() {
  return getTurnEngineType(currentGame.turn) || getTurnEngineType('w') || getTurnEngineType('b') || ENGINE_TYPES[0]
}

function engineSourceTag(source) {
  return isEngineMoveSource(source)
    ? `<span class="engine-tag">[${source}]</span>`
    : ''
}

function resolveEngineUrl(engineType) {
  const explicit = sanitizeEngineUrl(engineUrlEl.value)
  if (explicit) {
    return explicit
  }

  const runtime = getRuntimeEngineUrl(engineType)
  if (runtime) {
    return runtime
  }

  if (isGitHubPagesHost()) {
    return ''
  }

  return DEFAULT_LOCAL_ENGINE_URLS[engineType] || ''
}

function boardMoveToSan(boardMove) {
  const from = String(boardMove.from || '').toLowerCase()
  const to = String(boardMove.to || '').toLowerCase()
  const promotion = boardMove.promotion ? String(boardMove.promotion).toLowerCase() : ''

  if (!from || !to) {
    throw new Error('Board move is missing from/to squares.')
  }

  return `${from}${to}${promotion}`
}

function boardMoveStringToSan(moveString) {
  const source = String(moveString || '').trim()
  const match = source.match(/^([A-L](?:10|11|[1-9]))(?:-|x)([A-L](?:10|11|[1-9]))(?:[pPnNqQrRbB])?(?:\$)?(?:=([QqRrBbNn]))?$/)

  if (!match) {
    throw new Error(`Invalid board move string: ${source}`)
  }

  const from = match[1].toLowerCase()
  const to = match[2].toLowerCase()
  const promotion = match[3] ? match[3].toLowerCase() : ''

  return `${from}${to}${promotion}`
}

function parseEngineSan(source) {
  const match = String(source).trim().match(/^([a-l](?:10|11|[1-9]))([a-l](?:10|11|[1-9]))([nbrq])?$/i)
  if (!match) {
    throw new Error(`Invalid engine SAN: ${source}`)
  }

  return {
    from: match[1].toUpperCase(),
    to: match[2].toUpperCase(),
    promotion: match[3] ? match[3].toUpperCase() : null,
  }
}

function groupedMoves() {
  const rows = []
  for (let i = 0; i < moveHistory.length; i += 2) {
    rows.push({
      number: Math.floor(i / 2) + 1,
      white: moveHistory[i] || null,
      black: moveHistory[i + 1] || null,
      whiteIndex: i + 1,
      blackIndex: i + 2,
    })
  }
  return rows
}

function renderHistory() {
  const rows = groupedMoves()
  if (rows.length === 0) {
    historyEl.innerHTML = '<div style="padding:0.6rem;" class="muted">No moves recorded yet.</div>'
  } else {
    const html = [
      '<table>',
      '<thead><tr><th>#</th><th>White</th><th>Black</th></tr></thead>',
      '<tbody>',
    ]

    for (const row of rows) {
      const white = row.white
      const black = row.black

      html.push('<tr>')
      html.push(`<td>${row.number}</td>`)

      if (white) {
        const activeClass = historyIndex === row.whiteIndex ? 'active' : ''
        const details = white.evaluations != null && white.duration != null
          ? ` <span class="muted">(${white.evaluations.toLocaleString()} evals, ${Math.round(white.duration)}ms)</span>`
          : ''
        const source = engineSourceTag(white.source)
        html.push(`<td class="${activeClass}"><button data-jump="${row.whiteIndex}">${white.san}</button>${source}${details}</td>`)
      } else {
        html.push('<td></td>')
      }

      if (black) {
        const activeClass = historyIndex === row.blackIndex ? 'active' : ''
        const details = black.evaluations != null && black.duration != null
          ? ` <span class="muted">(${black.evaluations.toLocaleString()} evals, ${Math.round(black.duration)}ms)</span>`
          : ''
        const source = engineSourceTag(black.source)
        html.push(`<td class="${activeClass}"><button data-jump="${row.blackIndex}">${black.san}</button>${source}${details}</td>`)
      } else {
        html.push('<td></td>')
      }

      html.push('</tr>')
    }

    html.push('</tbody></table>')
    historyEl.innerHTML = html.join('')
  }

  historySummaryEl.textContent = `Move ${historyIndex} / ${moveHistory.length}`

  navStartBtn.disabled = historyIndex === 0
  navBackBtn.disabled = historyIndex === 0
  navForwardBtn.disabled = historyIndex >= moveHistory.length
  navEndBtn.disabled = historyIndex >= moveHistory.length
}

function rebuildGameTo(index) {
  const game = Hexchess.parse(startFen)
  for (let i = 0; i < index; i += 1) {
    game.applyMove(moveHistory[i].san)
  }
  return game
}

function applySanToBoard(san) {
  const parsed = parseEngineSan(san)
  const moved = boardEl.move(parsed.from, parsed.to)
  if (!moved) {
    throw new Error(`Board rejected move: ${san}`)
  }

  if (parsed.promotion) {
    const promoted = boardEl.promote(parsed.promotion)
    if (!promoted) {
      throw new Error(`Board rejected promotion: ${san}`)
    }
  }
}

function sanToBoardMove(san) {
  const parsed = parseEngineSan(san)
  return {
    from: parsed.from,
    to: parsed.to,
    promotion: parsed.promotion,
  }
}

function syncBoardToHistory(index) {
  const baseGame = Hexchess.parse(startFen)
  const boardFen = toBoardComponentFen(baseGame)
  const boardTurn = baseGame.turn === 'b' ? 'black' : 'white'

  boardEl.stopCustomEvents()
  suppressBoardMoveEvent = true

  try {
    // Hard reset internal widget state (captured pieces, score, move stack).
    if (typeof boardEl.reset === 'function') {
      boardEl.reset()
    }
    boardEl.setAttribute('board', boardFen)
    boardEl.setAttribute('turn', boardTurn)
    boardEl.setAttribute('moves', '')
    boardEl.unfreeze()
    boardEl.moves = moveHistory.slice(0, index).map((entry) => sanToBoardMove(entry.san))
    if (index > 0) {
      boardEl.fastForwardAll()
    }
  } finally {
    suppressBoardMoveEvent = false
    boardEl.restartCustomEvents()
  }
}

function jumpTo(index) {
  const clamped = Math.max(0, Math.min(index, moveHistory.length))
  const previousIndex = historyIndex

  if (clamped !== previousIndex) {
    boardEl.stopCustomEvents()
    suppressBoardMoveEvent = true

    try {
      const steps = clamped - previousIndex
      if (steps > 0) {
        for (let i = 0; i < steps; i += 1) {
          boardEl.fastForward()
        }
      } else {
        for (let i = 0; i < Math.abs(steps); i += 1) {
          boardEl.rewind()
        }
      }
    } catch {
      // Fallback to full sync if relative navigation fails for any reason.
      syncBoardToHistory(clamped)
    } finally {
      suppressBoardMoveEvent = false
      boardEl.restartCustomEvents()
    }
  }

  historyIndex = clamped
  currentGame = rebuildGameTo(historyIndex)
  renderHistory()
}

function appendMove(san, meta = {}) {
  if (historyIndex < moveHistory.length) {
    moveHistory = moveHistory.slice(0, historyIndex)
  }

  const snapshotBefore = currentGame.toString()
  currentGame.applyMove(san)

  moveHistory.push({
    san,
    source: meta.source || 'manual',
    beforeFen: snapshotBefore,
    evaluations: meta.evaluations ?? null,
    duration: meta.duration ?? null,
    metrics: meta.metrics ?? null,
  })

  historyIndex = moveHistory.length
  renderHistory()
}

function currentPositionHistory() {
  return moveHistory
    .slice(0, historyIndex)
    .map((entry) => entry.beforeFen)
    .filter((fen) => typeof fen === 'string' && fen.length > 0)
}

function setBusy(nextBusy) {
  isBusy = nextBusy
  playEngineBtn.disabled = nextBusy
  pingBtn.disabled = nextBusy
  toggleMatchBtn.disabled = false
}

async function executeEngine(engineType, command, options = {}) {
  const engineUrl = resolveEngineUrl(engineType)
  if (!engineUrl) {
    throw new Error(`Engine URL is required for ${engineType}.`)
  }

  const response = await fetch(`${engineUrl}/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command, options }),
  })

  if (!response.ok) {
    const body = await response.text()
    throw new Error(`Engine request failed (${response.status}): ${body}`)
  }

  return response.json()
}

async function pingEngine() {
  setBusy(true)
  try {
    const engineType = getPreferredEngineType()
    const data = await executeEngine(engineType, 'hexchess/ping', {})
    setStatus(`${engineType} is reachable. Timestamp: ${data.response?.now ?? 'n/a'}`)
  } catch (error) {
    setStatus(String(error.message || error), true)
  } finally {
    setBusy(false)
  }
}

async function playEngineMove() {
  if (isBusy) {
    return false
  }

  const turn = currentGame.turn
  const engineType = getTurnEngineType(turn)
  if (!engineType) {
    setStatus(`Turn ${turn === 'w' ? 'white' : 'black'} is set to Human.`)
    return false
  }

  setBusy(true)

  try {
    const startedAt = performance.now()
    const data = await executeEngine(engineType, 'hexchess/evaluate', {
      depth: getEngineDepth(),
      position: currentGame.toString(),
      positionHistory: currentPositionHistory(),
      diagnostics: true,
    })
    const duration = performance.now() - startedAt

    const best = data.response?.sans?.[0]
    if (!best || !best.san) {
      setStatus('Engine returned no legal moves.')
      return false
    }

    boardEl.stopCustomEvents()
    suppressBoardMoveEvent = true
    try {
      applySanToBoard(best.san)
    } finally {
      suppressBoardMoveEvent = false
      boardEl.restartCustomEvents()
    }

    appendMove(best.san, {
      source: engineType,
      evaluations: data.response?.evaluations ?? null,
      duration,
      metrics: data.response?.metrics ?? null,
    })

    evaluation = data.response
    setStatus(`${engineType} played ${best.san} (${Math.round(duration)}ms).`)
    return true
  } catch (error) {
    setStatus(String(error.message || error), true)
    return false
  } finally {
    setBusy(false)
  }
}

async function maybeAutoPlayEngineTurn() {
  if (isBusy) {
    return
  }

  if (historyIndex !== moveHistory.length) {
    return
  }

  if (!sideIsEngine(currentGame.turn)) {
    return
  }

  await playEngineMove()
}

async function runMatchLoop() {
  const token = ++matchToken
  toggleMatchBtn.textContent = 'Stop Match'
  setStatus('Engine match started.')

  for (let ply = 0; ply < 400; ply += 1) {
    if (token !== matchToken) {
      return
    }

    if (!sideIsEngine(currentGame.turn)) {
      setStatus('Match paused because current side is Human.')
      return
    }

    if (currentGame.isCheckmate() || currentGame.isStalemate()) {
      setStatus('Game over detected.')
      return
    }

    const moved = await playEngineMove()
    if (!moved) {
      return
    }
  }
}

function stopMatch() {
  matchToken += 1
  toggleMatchBtn.textContent = 'Start Match'
}

function resetGame() {
  stopMatch()
  startFen = START_FEN
  moveHistory = []
  historyIndex = 0
  evaluation = null
  currentGame = Hexchess.parse(startFen)
  syncBoardToHistory(historyIndex)
  renderHistory()
  setStatus('Reset to initial position.')
}

function saveGame() {
  const payload = {
    version: 1,
    startFen,
    historyIndex,
    engineUrl: sanitizeEngineUrl(engineUrlEl.value),
    whiteSide: whiteSideEl.value,
    blackSide: blackSideEl.value,
    depth: getEngineDepth(),
    moves: moveHistory,
    evaluation,
  }

  const yaml = YAML.stringify(payload)
  const blob = new Blob([yaml], { type: 'application/yaml' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  const stamp = new Date().toISOString().replace(/[:.]/g, '-')

  anchor.href = url
  anchor.download = `hexchess-game-${stamp}.yaml`
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)

  setStatus('Saved game to YAML.')
}

function isLoadedMove(item) {
  return item && typeof item.san === 'string'
}

async function loadGameFile(file) {
  const raw = await file.text()
  const parsed = YAML.parse(raw)

  if (!parsed || parsed.version !== 1 || typeof parsed.startFen !== 'string' || !Array.isArray(parsed.moves)) {
    throw new Error('Invalid game file format.')
  }

  if (!parsed.moves.every(isLoadedMove)) {
    throw new Error('Invalid moves in saved file.')
  }

  const loadedMoves = parsed.moves.map((move) => ({
    san: String(move.san),
    source: isEngineMoveSource(move.source) ? String(move.source) : 'manual',
    beforeFen: typeof move.beforeFen === 'string' ? move.beforeFen : null,
    evaluations: Number.isFinite(move.evaluations) ? move.evaluations : null,
    duration: Number.isFinite(move.duration) ? move.duration : null,
    metrics: move.metrics && typeof move.metrics === 'object' ? move.metrics : null,
  }))

  let preview = Hexchess.parse(parsed.startFen)
  for (const move of loadedMoves) {
    preview.applyMove(move.san)
  }

  startFen = parsed.startFen
  moveHistory = loadedMoves
  historyIndex = Number.isInteger(parsed.historyIndex)
    ? Math.max(0, Math.min(parsed.historyIndex, moveHistory.length))
    : moveHistory.length

  if (typeof parsed.engineUrl === 'string' && parsed.engineUrl.trim()) {
    engineUrlEl.value = sanitizeEngineUrl(parsed.engineUrl)
  }

  if (parsed.whiteSide === 'human' || isEngineType(parsed.whiteSide)) {
    whiteSideEl.value = parsed.whiteSide
  }

  if (parsed.blackSide === 'human' || isEngineType(parsed.blackSide)) {
    blackSideEl.value = parsed.blackSide
  }

  if (Number.isInteger(parsed.depth) && parsed.depth > 0) {
    engineDepthEl.value = String(Math.min(parsed.depth, 8))
  }

  currentGame = rebuildGameTo(historyIndex)
  syncBoardToHistory(historyIndex)
  renderHistory()
  setStatus(`Loaded ${moveHistory.length} moves from file.`)
}

boardEl.addEventListener('move', (event) => {
  if (suppressBoardMoveEvent) {
    return
  }

  try {
    let san = null
    const moveString = event?.detail?.move

    if (typeof moveString === 'string' && moveString.length > 0) {
      san = boardMoveStringToSan(moveString)
    } else {
      const latest = Array.isArray(boardEl.moves) ? boardEl.moves[boardEl.moves.length - 1] : null
      if (!latest) {
        return
      }
      san = boardMoveToSan(latest)
    }

    appendMove(san, { source: 'manual' })
    void maybeAutoPlayEngineTurn()
  } catch (error) {
    setStatus(String(error.message || error), true)
  }
})

boardEl.addEventListener('gameover', (event) => {
  const outcome = event?.detail?.outcome || 'unknown'
  setStatus(`Game over: ${outcome}`)
  stopMatch()
})

historyEl.addEventListener('click', (event) => {
  const target = event.target
  if (!(target instanceof HTMLElement)) {
    return
  }

  const jump = target.getAttribute('data-jump')
  if (!jump) {
    return
  }

  const index = Number(jump)
  if (!Number.isFinite(index)) {
    return
  }

  jumpTo(index)
})

pingBtn.addEventListener('click', () => {
  void pingEngine()
})

playEngineBtn.addEventListener('click', () => {
  void playEngineMove()
})

toggleMatchBtn.addEventListener('click', () => {
  if (toggleMatchBtn.textContent === 'Stop Match') {
    stopMatch()
    setStatus('Engine match stopped.')
    return
  }

  void runMatchLoop().finally(() => {
    stopMatch()
  })
})

flipBtn.addEventListener('click', () => {
  boardEl.flip()
})

flipTopPiecesBtn?.addEventListener('click', () => {
  toggleBlackPieceRotationMode()
})

resetBtn.addEventListener('click', () => {
  resetGame()
})

saveBtn.addEventListener('click', () => {
  saveGame()
})

loadBtn.addEventListener('click', () => {
  loadInputEl.click()
})

loadInputEl.addEventListener('change', async () => {
  const file = loadInputEl.files && loadInputEl.files[0]
  if (!file) {
    return
  }

  try {
    await loadGameFile(file)
  } catch (error) {
    setStatus(String(error.message || error), true)
  } finally {
    loadInputEl.value = ''
  }
})

navStartBtn.addEventListener('click', () => jumpTo(0))
navBackBtn.addEventListener('click', () => jumpTo(historyIndex - 1))
navForwardBtn.addEventListener('click', () => jumpTo(historyIndex + 1))
navEndBtn.addEventListener('click', () => jumpTo(moveHistory.length))

whiteSideEl.addEventListener('change', () => {
  stopMatch()
  void maybeAutoPlayEngineTurn()
})

blackSideEl.addEventListener('change', () => {
  stopMatch()
  void maybeAutoPlayEngineTurn()
})

engineDepthEl.addEventListener('change', () => {
  const depth = getEngineDepth()
  engineDepthEl.value = String(depth)
})

resetGame()
updatePieceRotationMode()
engineUrlEl.value = resolveInitialEngineUrl()
engineUrlEl.addEventListener('change', () => {
  persistEngineUrl(engineUrlEl.value)
})
setStatus('Ready. Configure sides and play.')
