# hexchess-board client

Do not open `index.html` directly via `file://`.

Modern browsers block JavaScript ES module loading from `file://` origins (`origin null`), which is why you see CORS errors for `app.js`.

Use a local HTTP server instead.

## Windows PowerShell

From repo root:

```powershell
./hexchess-board/start-server.ps1
```

Then open:

- http://127.0.0.1:4175/index.html

## Alternative (manual)

```powershell
cd hexchess-board
python -m http.server 4175 --bind 127.0.0.1
```

Open the same URL above.

## Engine Selection

The game setup now supports these engine-side values:

- `pyengine2`
- `pyrustengine`

Local defaults:

- `pyengine2` -> `http://127.0.0.1:8000`
- `pyrustengine` -> `http://127.0.0.1:8081`

If `app-config.js` provides a global `engineUrl`, that override is used for any selected engine. If it provides an `engineUrls` object, the client uses the matching per-engine base URL.

## pyengine2

Start pyengine2 separately:

```powershell
python -m uvicorn pyengine2.main:app --reload --host 127.0.0.1 --port 8000
```

## pyrustengine

Start pyrustengine separately:

```powershell
python -m pyrustengine
```

## GitHub Pages Engine URL Configuration

The client loads runtime config from `app-config.js`.

For GitHub Pages deploys, the workflow [.github/workflows/hexchess-board-pages.yml](../.github/workflows/hexchess-board-pages.yml)
injects a repository variable into that file.

1. In GitHub, open repository `Settings` -> `Secrets and variables` -> `Actions` -> `Variables`.
2. Create a variable named `PYENGINE2_BASE_URL`.
3. Set it to your HTTPS engine endpoint, for example:

```text
https://your-pyengine2.example.com
```

4. Run or let the `Deploy Hexchess Board Client` workflow run on `main`.

Notes:

- If `PYENGINE2_BASE_URL` is empty, GitHub Pages builds with an empty global engine URL and local defaults are used outside GitHub Pages.
- The UI also stores the last entered engine URL in localStorage.
