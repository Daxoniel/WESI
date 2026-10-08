import { build } from 'esbuild';
import { copyFile, mkdir } from 'node:fs/promises';

await mkdir('vendor', {recursive: true});
await build({entryPoints:['vendor-entry.js'], bundle:true, minify:true,
  format:'esm', legalComments:'eof', outfile:'vendor/number-flow.js'});
for (const [source, target] of [
  ['number-flow/LICENSE.md', 'NUMBERFLOW-LICENSE.md'],
  ['lucide/LICENSE', 'LUCIDE-LICENSE.txt'],
  ['esm-env/LICENSE', 'ESM-ENV-LICENSE.txt'],
  ['@fontsource-variable/inter/LICENSE', 'INTER-LICENSE.txt'],
  ['@fontsource-variable/inter/files/inter-latin-wght-normal.woff2', 'inter-latin.woff2'],
]) await copyFile(`node_modules/${source}`, `vendor/${target}`);

await copyFile('../assets/salary/coin.png', 'vendor/coin.png');
await copyFile('../assets/salary/KENNEY-LICENSE.txt', 'vendor/KENNEY-LICENSE.txt');
