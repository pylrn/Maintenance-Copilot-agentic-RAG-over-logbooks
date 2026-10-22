/** Static Vercel deployment with optional same-origin backend proxy. No secrets are bundled. */
import { cp, mkdir, writeFile, rm, access } from 'node:fs/promises';
import { resolve, join } from 'node:path';

const root = process.cwd();
const output = resolve(root, '.vercel/output');
const backend = process.env.MAINTENANCE_BACKEND_ORIGIN || '';
let origin = null;
if (backend) {
  const url = new URL(backend);
  if (url.protocol !== 'https:' || url.username || url.password || url.pathname !== '/' || url.search || url.hash || /^(localhost|127\.|0\.|\[?::1)/i.test(url.hostname)) {
    throw new Error('MAINTENANCE_BACKEND_ORIGIN must be a public HTTPS origin without credentials, path or query');
  }
  origin = url.origin;
}
await rm(output, { recursive: true, force: true });
await mkdir(join(output, 'static'), { recursive: true });
await cp(join(root, 'public'), join(output, 'static'), { recursive: true });
// Publish the same latest controller/modules at root and /maintenance/.
await cp(join(root, 'public/maintenance'), join(output, 'static'), { recursive: true });
for (const dir of ['', 'maintenance']) {
  await writeFile(join(output, 'static', dir, 'deployment-config.mjs'),
    `export const deploymentMode = ${JSON.stringify(origin ? 'live' : 'demo')};\n`);
}
await writeFile(join(output, 'static/backend-unavailable.json'), JSON.stringify({
  error: 'backend_not_configured', message: 'The deployed UI has no HTTPS backend configured. Local retrieval remains available on the development computer.', retryable: false
}));
await writeFile(join(output, 'static/deployment-status.json'), JSON.stringify({
  frontend: 'maintenance-atlas', mode: origin ? 'live' : 'demo', backend_configured: Boolean(origin),
  commit: process.env.VERCEL_GIT_COMMIT_SHA || null
}));
const routes = [
  { src: '/api/(.*)', dest: origin ? `${origin}/api/$1` : '/backend-unavailable.json',
    ...(origin ? {} : { status: 503 }), headers: { 'Cache-Control': 'no-store' } },
  { src: '/maintenance/?', dest: '/maintenance/index.html' },
  { src: '/', dest: '/index.html' },
  { src: '/(.*\\.mjs)', headers: { 'Content-Type': 'text/javascript; charset=utf-8', 'Cache-Control': 'public, max-age=0, must-revalidate' }, continue: true },
  { handle: 'filesystem' }
];
for (const file of ['maintenance/index.html', 'maintenance/maintenance-ui.mjs', 'maintenance/api-client.mjs', 'maintenance/demo-adapter.mjs']) {
  await access(join(output, 'static', file));
}
await writeFile(join(output, 'config.json'), JSON.stringify({ version: 3, routes }, null, 2));
console.log(`Maintenance Atlas built: ${origin ? 'live API proxy configured' : 'explicit demo; backend not configured'}`);
