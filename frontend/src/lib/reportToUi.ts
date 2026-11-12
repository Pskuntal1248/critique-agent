/**
 * Deterministic mapping from the writer's Markdown report to OpenUI Lang.
 * No model call. Anything not recognised stays as Prose (raw Markdown), so no
 * report content is dropped. Returns null when the report has no usable structure,
 * so the caller shows the plain Markdown view.
 */

const q = (s: string) => JSON.stringify(s);

type Block = { kind: 'prose' | 'table' | 'steps' | 'callout'; text: string; rows?: string[][]; items?: string[]; tone?: 'finding' | 'risk'; title?: string };

const RISK = /risk|limitation|caveat|uncertaint|open question|concern/i;
const STEPS = /step|plan|next|recommend|roadmap|timeline|how to/i;

function splitRow(line: string): string[] {
  return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());
}
const isSep = (l: string) => /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(l);

function blocksFor(heading: string, body: string[]): Block[] {
  const out: Block[] = [];
  let buf: string[] = [];
  const flush = () => {
    const text = buf.join('\n').trim();
    buf = [];
    if (!text) return;
    const lines = text.split('\n');
    const ordered = lines.length > 0 && lines.every((l) => /^\s*\d+[.)]\s+/.test(l));
    const quote = lines.every((l) => /^\s*>/.test(l));
    if (ordered && STEPS.test(heading) && !RISK.test(heading)) {
      out.push({ kind: 'steps', text, items: lines.map((l) => l.replace(/^\s*\d+[.)]\s+/, '')) });
    } else if (quote) {
      const t = lines.map((l) => l.replace(/^\s*>\s?/, '')).join('\n').trim();
      out.push({ kind: 'callout', text: t, tone: RISK.test(heading) ? 'risk' : 'finding', title: RISK.test(heading) ? 'Note' : 'Key point' });
    } else {
      out.push({ kind: 'prose', text });
    }
  };
  for (let i = 0; i < body.length; i++) {
    const l = body[i];
    if (l.includes('|') && i + 1 < body.length && isSep(body[i + 1])) {
      flush();
      const header = splitRow(l);
      const rows: string[][] = [];
      i += 2;
      while (i < body.length && body[i].includes('|') && body[i].trim() !== '') rows.push(splitRow(body[i++]));
      i--;
      if (rows.length && header.length > 1) out.push({ kind: 'table', text: '', rows: [header, ...rows] });
      else buf.push(l);
      continue;
    }
    if (l.trim() === '') { buf.push(l); continue; }
    buf.push(l);
  }
  flush();
  return out;
}

function domainOf(url: string): string {
  try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return ''; }
}

export function reportToOpenUi(markdown: string): string | null {
  const lines = markdown.replace(/\r\n/g, '\n').split('\n');
  let title = '';
  const sections: { heading: string; body: string[] }[] = [];
  const intro: string[] = [];
  let cur: { heading: string; body: string[] } | null = null;
  for (const l of lines) {
    const h1 = /^#\s+(.+)$/.exec(l);
    const h2 = /^##\s+(.+)$/.exec(l);
    if (h1 && !title && !cur) { title = h1[1].trim(); continue; }
    if (h2) { cur = { heading: h2[1].trim(), body: [] }; sections.push(cur); continue; }
    (cur ? cur.body : intro).push(l);
  }
  if (sections.length < 1) return null;

  const srcIdx = sections.findIndex((s) => /^sources?$|^references?$|^citations?$/i.test(s.heading));
  const srcSection = srcIdx >= 0 ? sections.splice(srcIdx, 1)[0] : null;
  const sources: { n: number; title: string; url: string }[] = [];
  if (srcSection) {
    for (const l of srcSection.body) {
      const m = /^\s*(?:(\d+)[.)]|[-*])\s+\[([^\]]+)\]\(([^)\s]+)\)/.exec(l);
      if (m) sources.push({ n: m[1] ? Number(m[1]) : sources.length + 1, title: m[2], url: m[3] });
    }
  }
  // Non-http(s) links stay as plain-text sources (the Source component renders no anchor for them).
  const safeSources = sources;

  const stmts: string[] = [];
  const secNames: string[] = [];
  let id = 0;
  const next = (p: string) => `${p}${++id}`;
  for (const s of sections) {
    const names: string[] = [];
    for (const b of blocksFor(s.heading, s.body)) {
      const n = next('b');
      names.push(n);
      if (b.kind === 'table' && b.rows) stmts.push(`${n} = Compare(${q("")}, ${JSON.stringify(b.rows[0])}, ${JSON.stringify(b.rows.slice(1))})`);
      else if (b.kind === 'steps') stmts.push(`${n} = Steps(${q('Steps')}, ${JSON.stringify(b.items)})`);
      else if (b.kind === 'callout') stmts.push(`${n} = Callout(${q(b.tone!)}, ${q(b.title!)}, ${q(b.text)})`);
      else stmts.push(`${n} = Prose(${q(b.text)})`);
    }
    if (!names.length) continue;
    const sn = next('s');
    secNames.push(sn);
    stmts.push(`${sn} = Section(${q(s.heading)}, [${names.join(', ')}])`);
  }
  if (!secNames.length) return null;
  const srcNames = safeSources.map((s) => {
    const n = next('r');
    stmts.push(`${n} = Source(${s.n}, ${q(s.title)}, ${q(domainOf(s.url))}, ${q(s.url)})`);
    return n;
  });
  const summary = intro.join('\n').trim();
  const root = `root = Report(${q(title || 'Research report')}, ${q(summary)}, [${secNames.join(', ')}], [${srcNames.join(', ')}])`;
  return [root, ...stmts].join('\n');
}
