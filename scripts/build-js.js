import fs from 'node:fs'
import { copy, execAsync, read, resolve, write } from './utils.js'

function resolveCliPath(...candidates) {
  for (const candidate of candidates) {
    const file = resolve(candidate)
    if (fs.existsSync(file)) {
      return file
    }
  }

  throw new Error(`Unable to locate CLI script. Tried: ${candidates.join(', ')}`)
}

/** build js library for npm */
export async function buildJs(options) {
  // cleanup
  await execAsync('rm', ['-rf', resolve('js/dist')], {
    cwd: 'js',
    silent: options?.silent,
  })

  // generate types
  const tscPath = resolveCliPath('js/node_modules/typescript/bin/tsc', 'node_modules/typescript/bin/tsc')
  await execAsync(process.execPath, [tscPath, '--project', './tsconfig.json', '--emitDeclarationOnly'], {
    cwd: 'js',
  })

  // build npm package
  const rollupPath = resolveCliPath('js/node_modules/rollup/dist/bin/rollup', 'node_modules/rollup/dist/bin/rollup')
  await execAsync(process.execPath, [rollupPath, '--config', 'rollup.config.ts', '--configPlugin', '@rollup/plugin-typescript'], {
    cwd: 'js',
  })

  copy('LICENSE', 'js/dist/LICENSE')
  copy('js/package.json', 'js/dist/package.json')
  copy('README.md', 'js/dist/README.md')

  // set version numbers
  const pkg = JSON.parse(read('js/package.json'))
  write('js/dist/index.mjs', read('js/dist/index.mjs').replace('x.y.z', pkg.version))
}