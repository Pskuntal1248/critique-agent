'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ByokSettings, DEMO_API, fetchAuthConfig, fetchMe, GOOGLE_LOGIN_URL, loadSettings, saveSettings } from '@/lib/api';

export default function SettingsPage() {
  const [settings, setSettings] = useState<ByokSettings>({provider: 'openrouter', model: '', key: ''});
  const [models, setModels] = useState<string[]>([]);
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);
  const [acct, setAcct] = useState<'loading' | 'off' | 'out' | string>('loading');
  useEffect(() => { setSettings(loadSettings()); }, []);
  useEffect(() => {
    Promise.all([fetchAuthConfig(), fetchMe()]).then(([c, me]) => setAcct(me ? me.email : c.google ? 'out' : 'off'));
  }, []);
  async function fetchModels() {
    setBusy(true); setStatus('Contacting your provider. The free backend may take a minute to wake up.');
    try {
      const r = await fetch(`${DEMO_API}/byok/models`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({provider: settings.provider, key: settings.key})});
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'Could not load models.');
      setModels(data.models); setStatus(`${data.models.length} models loaded. Choose one below.`);
    } catch (e) { setStatus(e instanceof Error ? e.message : 'Could not load models.'); }
    finally { setBusy(false); }
  }
  const field = 'w-full border border-line p-3 bg-white text-ink rounded-none';
  return <section className="max-w-2xl mx-auto space-y-6">
    <div><h1 className="text-3xl font-bold">Your model settings</h1><p className="text-muted mt-2">Bring your own API key. No shared server key and no subscription to this demo.</p></div>
    <div className="border border-line p-4 text-sm space-y-2">
      <p>Your key is kept in this tab&apos;s session storage, not in the server environment or database. It is sent over HTTPS to this app&apos;s backend for model lookup and research, held only in task memory, and forwarded only to your selected provider.</p>
      <p>Closing the tab clears the saved key. Do not use a shared computer. Your provider may charge for calls; use its budget controls or a free model. Do not enter private or confidential research.</p>
    </div>
    <div className="border border-line p-4 text-sm space-y-2">
      <p className="font-medium">Account</p>
      {acct === 'loading' && <p className="text-muted">Checking account support...</p>}
      {acct === 'off' && <p>Accounts are not set up on this deployment. Reports are kept for this browser session only and are lost when the server restarts. Use Download .md or .json on a finished report to keep it.</p>}
      {acct === 'out' && <p>Not signed in. <a className="underline" href={GOOGLE_LOGIN_URL}>Sign in with Google</a> to keep your reports across sessions. Your provider key stays in this tab either way.</p>}
      {!['loading','off','out'].includes(acct) && <p>Signed in as {acct}. Your reports are saved to your account. Your provider key is not saved to it.</p>}
    </div>
    <label className="block space-y-2"><span>Provider</span><select className={field} value={settings.provider} onChange={e=>{setSettings({...settings, provider:e.target.value, model:''});setModels([]);}}>
      <option value="openrouter">OpenRouter</option><option value="openai">OpenAI</option><option value="anthropic">Anthropic</option><option value="gemini">Google Gemini</option><option value="groq">Groq</option>
    </select></label>
    <label className="block space-y-2"><span>API key</span><input className={field} type="password" autoComplete="off" value={settings.key} onChange={e=>setSettings({...settings,key:e.target.value})} placeholder="Paste your own provider key" /></label>
    <button disabled={busy || !settings.key} className="bg-accent px-5 py-2 font-medium disabled:opacity-40" onClick={fetchModels}>{busy?'Loading...':'Load provider models'}</button>
    {models.length>0 && <label className="block space-y-2"><span>Provider models</span><select className={field} value={settings.model} onChange={e=>setSettings({...settings,model:e.target.value})}><option value="">Choose a model</option>{models.map(m=><option key={m} value={m}>{m}</option>)}</select></label>}
    <label className="block space-y-2"><span>Model ID {models.length===0?'(or enter one directly)':''}</span><input className={field} value={settings.model} onChange={e=>setSettings({...settings,model:e.target.value})} placeholder="Provider model ID" /></label>
    <p className="text-sm text-muted">Choose a chat model that supports tool calling. OpenRouter model IDs ending in :free are free models, subject to provider limits. Model access and prices are set by your provider.</p>
    <div className="flex gap-4"><button disabled={!settings.key || !settings.model} className="bg-accent px-5 py-2 font-medium disabled:opacity-40" onClick={()=>{saveSettings(settings);setStatus('Saved for this tab. You can now start a research task.');}}>Save settings</button><button className="border border-line px-4 py-2" onClick={()=>{sessionStorage.removeItem('critique.byok');setSettings({...settings,key:''});setStatus('Key cleared from this tab.');}}>Clear key</button></div>
    <p role="status" className="text-sm">{status}</p>
    <Link href="/tasks/new" className="inline-block underline">Start a research task</Link>
  </section>;
}
