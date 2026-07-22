import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const dist = path.join(root, 'dist');
const required = ['index.html', 'sw.js', 'manifest.webmanifest', 'asset-manifest.json'];
const missing = required.filter((file) => !existsSync(path.join(dist, file)));
if (missing.length) throw new Error(`Missing offline build artifacts: ${missing.join(', ')}`);

const index = readFileSync(path.join(dist, 'index.html'), 'utf8');
if (!index.includes('rel="manifest"') || !index.includes('/manifest.webmanifest')) {
  throw new Error('Production index does not link the web app manifest.');
}

const serviceWorker = readFileSync(path.join(dist, 'sw.js'), 'utf8');
for (const boundary of ["'/api/'", "'/media/'", "'Authorization'", "request.method !== 'GET'"]) {
  if (!serviceWorker.includes(boundary)) throw new Error(`Service worker cache boundary missing: ${boundary}`);
}

const manifest = JSON.parse(readFileSync(path.join(dist, 'asset-manifest.json'), 'utf8'));
const assets = Object.values(manifest).flatMap((entry) => [
  entry.file,
  ...(entry.css ?? []),
  ...(entry.assets ?? []),
]).filter(Boolean);
const missingAssets = [...new Set(assets)].filter((file) => !existsSync(path.join(dist, file)));
if (missingAssets.length) throw new Error(`Asset manifest references missing files: ${missingAssets.join(', ')}`);

console.log(`Offline build verified: ${new Set(assets).size} versioned assets.`);
