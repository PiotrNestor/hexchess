# [`hexchess`](https://docs.hexchess.club)

[![Build](https://github.com/scottbedard/hexchess/actions/workflows/build.yml/badge.svg)](https://github.com/scottbedard/hexchess/actions/workflows/build.yml)
[![Coverage](https://codecov.io/gh/scottbedard/hexchess/graph/badge.svg?token=uHmFqhQDps)](https://codecov.io/gh/scottbedard/hexchess)
[![Crates.io](https://img.shields.io/crates/v/hexchess?label=cargo)](https://crates.io/crates/hexchess)
[![Packagist](https://img.shields.io/packagist/v/bedard/hexchess?color=%23777BB3)](https://packagist.org/packages/bedard/hexchess)
[![NPM](https://img.shields.io/npm/v/%40bedard%2Fhexchess?color=orange)](https://www.npmjs.com/package/@bedard/hexchess)
[![Engine version](https://img.shields.io/npm/v/%40bedard%2Fhexchess-engine?label=engine&color=orange)](https://www.npmjs.com/package/@bedard/hexchess-engine)
[![License](https://img.shields.io/badge/license-MIT-blue)](https://github.com/scottbedard/hexchess/blob/main/LICENSE)

A cross-language library for [Gliński's hexagonal chess](https://en.wikipedia.org/wiki/Hexagonal_chess#Gli%C5%84ski's_hexagonal_chess), and the brain of [hexchess.club](https://hexchess.club).

[View documentation &rarr;](https://docs.hexchess.club)

<p align="center">
  <a href="https://docs.hexchess.club">
    <img src="docs/public/hexchess.svg" width="540" />
  </a>
</p>


## Local Development

Depending on which library you're working on, you'll need to install a few dependencies.

- [Rust](https://www.rust-lang.org/tools/install)
- [PHP](https://www.php.net/)
- [Node.js](https://nodejs.org/) and [pnpm](https://pnpm.io/installation)
- [Python](https://www.python.org/) (for the optional FastAPI engine)

First, clone the repository, and setup the CLI.

```
git clone git@github.com:scottbedard/hexchess.git

cd hexchess

pnpm install
```

Next run `node hexchess` to see the following commands.

```
Usage: hexchess [options] [command]

Options:
  -h, --help                   display help for command

Commands:
  build                        Build all projects
  build:engine                 Build engine package
  build:js                     Build NPM package
  build:rs                     Build Rust crate
  docs:dev                     Develop docs
  docs:build                   Build docs
  docs:preview                 Preview docs
  lint:php                     Run linting
  test                         Run all tests
  test:engine [options]        Run engine tests
  test:js [options]            Run JavaScript tests
  test:php [options]           Run PHP tests
  test:rs [options]            Run Rust tests
  version [options] [version]  Set the version of the project
  version:check [options]      Check the versions of the dependencies
  help [command]               display help for command
```

### Python engine

The `pyengine` package exposes the same engine command interface over FastAPI.

```sh
python -m venv .venv
.venv/Scripts/activate
pip install -r pyengine/requirements.txt
uvicorn pyengine.main:app --reload --host 127.0.0.1 --port 8000
```

Then open the docs sandbox and pick `Python (FastAPI)` from the engine selector.

### Cython engine

The `cyengine` package is a compiled Cython variant of the Python engine. It keeps the same FastAPI contract and engine command shape, but builds the core engine module as a native extension.

```sh
python -m venv .venv
.venv/Scripts/activate
pip install -r cyengine/requirements.txt
pip install -e ./cyengine
uvicorn cyengine.main:app --reload --host 127.0.0.1 --port 8001
```

Run `python -m unittest cyengine.test_native_engine` after building to validate the compiled engine.

## License

[MIT](https://github.com/scottbedard/hexchess/blob/main/LICENSE)

Copyright (c) 2024-present, Scott Bedard
