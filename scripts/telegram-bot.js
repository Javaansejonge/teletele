// Node 20+, no deps. Long polling bot that triggers GitHub Actions via repository_dispatch.
import fs from 'node:fs/promises';

const {
  TELEGRAM_BOT_TOKEN,
  ALLOWED_CHAT_IDS = '',
  GITHUB_TOKEN,
  GITHUB_REPO,
  DEFAULT_BRANCH = 'main',
} = process.env;

if (!TELEGRAM_BOT_TOKEN || !GITHUB_TOKEN || !GITHUB_REPO) {
  console.error('Missing env: TELEGRAM_BOT_TOKEN, GITHUB_TOKEN, GITHUB_REPO');
  process.exit(1);
}

const API = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}`;
const ALLOWED = new Set(ALLOWED_CHAT_IDS.split(',').map(s => s.trim()).filter(Boolean));

let offset = 0;
const STATE_FILE = '/tmp/immorage-telegram-state.json';
const state = { lastRunId: null, defaultBranch: DEFAULT_BRANCH };

async function loadState() {
  try {
    const s = JSON.parse(await fs.readFile(STATE_FILE, 'utf8'));
    Object.assign(state, s);
  } catch {}
}
async function saveState() {
  await fs.writeFile(STATE_FILE, JSON.stringify(state), 'utf8');
}

async function tg(method, body) {
  const res = await fetch(`${API}/${method}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
  const j = await res.json();
  if (!j.ok) throw new Error(`Telegram error: ${JSON.stringify(j)}`);
  return j.result;
}

async function gh(path, init = {}) {
  const res = await fetch(`https://api.github.com${path}`, {
    ...init,
    headers: {
      'authorization': `Bearer ${GITHUB_TOKEN}`,
      'accept': 'application/vnd.github+json',
      ...(init.headers || {}),
    },
  });
  if (!res.ok) throw new Error(`GitHub ${res.status}: ${await res.text()}`);
  return res.json();
}

function helpText() {
  return [
    '🤖 *Immorage42 Mobile Control*',
    '',
    '/help – Befehlsübersicht',
    '/branch <name> – Standard-Branch setzen/anzeigen',
    '/pentest [args] – Harness anstoßen (repository_dispatch: pentest)',
    '/e2e [args] – E2E-Tests starten',
    '/deploy [env] – Deploy-Workflow starten',
    '/status [workflow] – Letzte Runs anzeigen',
    '/logs [run_number|latest] – Logs-URL des Runs',
  ].join('\n');
}

async function dispatch(eventType, payload = {}) {
  return gh(`/repos/${GITHUB_REPO}/dispatches`, {
    method: 'POST',
    body: JSON.stringify({ event_type: eventType, client_payload: payload }),
  });
}

async function listRuns(workflow = null) {
  // If workflow is provided, query that; else list repo runs
  if (workflow) {
    return gh(`/repos/${GITHUB_REPO}/actions/workflows/${encodeURIComponent(workflow)}/runs?per_page=5`);
  }
  return gh(`/repos/${GITHUB_REPO}/actions/runs?per_page=5`);
}

async function getRun(runId) {
  return gh(`/repos/${GITHUB_REPO}/actions/runs/${runId}`);
}

function ensureAllowed(chatId) {
  if (ALLOWED.size === 0) return true; // if not set, allow all (optional)
  return ALLOWED.has(String(chatId));
}

async function handleCommand(chatId, text) {
  if (!ensureAllowed(chatId)) {
    await tg('sendMessage', { chat_id: chatId, text: 'Not authorized.' });
    return;
  }

  const [cmd, ...rest] = text.trim().split(/\s+/);
  const args = rest.join(' ');

  try {
    switch (true) {
      case /^\/help/i.test(cmd): {
        await tg('sendMessage', { chat_id: chatId, text: helpText(), parse_mode: 'Markdown' });
        break;
      }
      case /^\/branch/i.test(cmd): {
        if (args) state.defaultBranch = args;
        await saveState();
        await tg('sendMessage', { chat_id: chatId, text: `🟢 Branch: ${state.defaultBranch}` });
        break;
      }
      case /^\/pentest/i.test(cmd): {
        await tg('sendMessage', { chat_id: chatId, text: '🛡️ Starte Pen‑Test Harness…' });
        await dispatch('pentest', { branch: state.defaultBranch, command: args || 'default' });
        await tg('sendMessage', { chat_id: chatId, text: '✅ Dispatch gesendet: pentest' });
        break;
      }
      case /^\/e2e/i.test(cmd): {
        await tg('sendMessage', { chat_id: chatId, text: '🧪 Starte E2E…' });
        await dispatch('e2e', { branch: state.defaultBranch, command: args || 'npm run test:e2e' });
        await tg('sendMessage', { chat_id: chatId, text: '✅ Dispatch gesendet: e2e' });
        break;
      }
      case /^\/deploy/i.test(cmd): {
        const env = args || 'preview';
        await tg('sendMessage', { chat_id: chatId, text: `🚀 Deploy (${env})…` });
        await dispatch('deploy', { branch: state.defaultBranch, env });
        await tg('sendMessage', { chat_id: chatId, text: `✅ Dispatch gesendet: deploy (${env})` });
        break;
      }
      case /^\/status/i.test(cmd): {
        const wf = args || null; // e.g. "ci.yml" or "pentest.yml"
        const data = await listRuns(wf);
        const runs = (data.workflow_runs || data.workflow_runs === undefined ? data.workflow_runs : data.workflow_runs) ?? data.runs ?? data.workflow_runs;
        const list = (runs || data.workflow_runs || data.runs || []).slice(0, 5).map(r =>
          `#${r.run_number} • ${r.name} • ${r.head_branch} • ${r.status}/${r.conclusion ?? '—'}`
        ).join('\n');
        await tg('sendMessage', { chat_id: chatId, text: list || 'Keine Runs gefunden.' });
        break;
      }
      case /^\/logs/i.test(cmd): {
        let runId = args.trim();
        if (!runId || runId === 'latest') {
          const data = await listRuns();
          const runs = data.workflow_runs || data.runs || [];
          if (!runs.length) return tg('sendMessage', { chat_id: chatId, text: 'Keine Runs.' });
          runId = runs[0].id;
          state.lastRunId = runId;
          await saveState();
        }
        const run = await getRun(runId);
        const url = run?.html_url || `https://github.com/${GITHUB_REPO}/actions/runs/${runId}`;
        await tg('sendMessage', { chat_id: chatId, text: `🗒️ Logs: ${url}` });
        break;
      }
      default: {
        await tg('sendMessage', { chat_id: chatId, text: 'Unbekannter Befehl. /help für Übersicht.' });
      }
    }
  } catch (e) {
    await tg('sendMessage', { chat_id: chatId, text: `❌ Fehler: ${e.message}` });
  }
}

async function loop() {
  await loadState();
  while (true) {
    try {
      const res = await fetch(`${API}/getUpdates`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ offset, timeout: 50 }), // long polling
      });
      const j = await res.json();
      if (j.ok && Array.isArray(j.result)) {
        for (const upd of j.result) {
          offset = upd.update_id + 1;
          const msg = upd.message || upd.edited_message;
          if (!msg || !msg.text) continue;
          const chatId = msg.chat.id;
          const text = msg.text.trim();
          if (text.startsWith('/')) {
            await handleCommand(chatId, text);
          }
        }
      }
    } catch (e) {
      console.error('poll error:', e.message);
      await new Promise(r => setTimeout(r, 2000));
    }
  }
}

loop();
