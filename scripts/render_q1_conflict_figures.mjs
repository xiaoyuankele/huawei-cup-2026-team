// Optional 300 dpi PNG rendering from the final PDF figures.
// npm dependencies: pdfjs-dist, @napi-rs/canvas. No browser or network is used.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
const local = createRequire(import.meta.url);
const req = process.env.WPC_NODE_MODULES ? createRequire(path.join(process.env.WPC_NODE_MODULES, '_resolver.cjs')) : local;
const { createCanvas, DOMMatrix, ImageData, Path2D } = req('@napi-rs/canvas');
Object.assign(globalThis, { DOMMatrix, ImageData, Path2D });
const pdfDir = path.dirname(req.resolve('pdfjs-dist/package.json'));
const pdfjs = await import(pathToFileURL(path.join(pdfDir, 'legacy/build/pdf.mjs')).href);
const here = path.dirname(fileURLToPath(import.meta.url));
const root = process.argv[2] || path.resolve(here, '../experiments/runs/q1-conflict-trial-20260924-r01');
const dir = path.join(root, 'figures');
for (const f of fs.readdirSync(dir).filter(f => f.endsWith('.pdf'))) {
  const doc = await pdfjs.getDocument({ data: new Uint8Array(fs.readFileSync(path.join(dir, f))), useSystemFonts: true }).promise;
  if (doc.numPages !== 1) throw new Error(`Expected one-page figure: ${f}`);
  const page = await doc.getPage(1);
  const vp = page.getViewport({ scale: 300 / 72 });
  const canvas = createCanvas(Math.ceil(vp.width), Math.ceil(vp.height));
  await page.render({ canvasContext: canvas.getContext('2d'), viewport: vp }).promise;
  fs.writeFileSync(path.join(dir, f.replace(/\.pdf$/, '.png')), canvas.toBuffer('image/png'));
  console.log(`Rendered ${f}`);
}
