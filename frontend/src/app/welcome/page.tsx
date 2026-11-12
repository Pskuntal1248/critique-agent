import Link from 'next/link';
import type { Metadata } from 'next';
import './landing.css';

export const metadata: Metadata = {
  title: 'Critique: research that argues with itself',
  description: 'Plan, search, analyse, challenge and approve. A research workbench that runs on your own model key.',
};

const API_DOCS_URL = `${process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'}/docs`;

export default function WelcomePage() {
  return (
    <div className="lp">


<div className="wrap hero">
 <span className="tag">Illustrated with sample data</span>
 <h1 style={{ marginTop: '22px' }}>Research that<br />argues with itself.</h1>
 <p className="lead">Critique plans a question, researches the web, drafts an analysis, then makes a critic challenge it. You read the draft before the report is written.</p>
 <div className="cta"><Link className="btn" href="/tasks/new">Start a research task</Link><a className="link" href="#sample-report">See a sample report</a></div>
 <div className="small">Bring your own model key. No account needed to try it.</div>

 <div className="win"><div className="bar"><span><i>Run</i> · UPI-led fintech: top 3 opportunities</span><span>sample run</span></div>
  <div className="grid"><div className="steps">
   <div className="st"><span className="dot"></span><div>Planner<small>3 sub-questions</small></div></div>
   <div className="st"><span className="dot"></span><div>Researcher<small>9 sources read</small></div></div>
   <div className="st"><span className="dot"></span><div>Analyst<small>draft 1 written</small></div></div>
   <div className="st"><span className="dot warn"></span><div>Critic<small>score 0.62, sent back</small></div></div>
   <div className="st"><span className="dot"></span><div>Analyst<small>draft 2, table added</small></div></div>
   <div className="st"><span className="dot"></span><div>Critic<small>score 0.81, approved</small></div></div>
   <div className="st"><span className="dot run"></span><div>Waiting for your review<small>final report not written</small></div></div>
  </div>
  <div className="draft"><h4>Analysis draft</h4>
   <div className="score"><b>0.81</b><span className="small">critic score after 1 revision</span></div>
   <p>Three segments stand out: merchant lending on UPI rails, credit on UPI, and payments infrastructure for small businesses [1][2].</p>
   <div className="cmt"><b>Critic:</b> No comparison across players. Add a table with sources.</div>
   <div className="fade"><table><tbody><tr><th>Segment</th><th>Signal</th><th>Main risk</th></tr><tr><td>Merchant lending</td><td>Strong</td><td>Credit losses</td></tr><tr><td>Credit on UPI</td><td>Early</td><td>Regulation</td></tr><tr><td>SMB infrastructure</td><td>Steady</td><td>Thin margins</td></tr></tbody></table></div>
   <div className="actions"><span className="p">Approve and write report</span><span>Send feedback</span><span>Reject</span></div>
  </div></div></div>
</div>

<div className="wrap"><section>
 <div className="head"><h2>A second opinion built into the run.</h2><p className="lead">Search and citations are table stakes. Critique&apos;s difference is the structure: you can see each step, challenge it, and stop it before a report exists.</p></div>
 <div className="bento">
  <div className="card dark c3"><h3>The critic pushes back</h3><p>Each draft gets a score and written feedback. Low scores go back to the analyst, up to a limit. It is a model&apos;s judgement, not a fact check.</p><div className="bars"><div></div><div></div><div></div></div><div className="small">sample scores: 0.45, 0.62, 0.81</div></div>
  <div className="card c3"><h3>You approve before it is written</h3><p>The run pauses on the full analysis draft, with sources and critic notes beside it. Comment, ask for changes or approve.</p><span className="pill">Approve</span><span className="pill">Send feedback</span><span className="pill">Reject</span></div>
  <div className="card c2"><h3>Cited reports</h3><p>Sources are listed and linked so you can check them.</p><div className="src"><span>[1]</span>Example source title one</div><div className="src"><span>[2]</span>Example source title two</div></div>
  <div className="card c2"><h3>Your key, your cost</h3><p>No shared server key. Pick a provider and paste your own.</p><div className="key"><input value="sk-••••••••••••" readOnly /><span className="pill" style={{ margin: '0' }}>Load models</span></div></div>
  <div className="card c2"><h3>Every step on record</h3><p>Agent, status, tokens and duration, per step.</p><div className="row"><b>Planner</b>completed<em>347 tok</em></div><div className="row"><b>Researcher</b>completed<em>9.9k tok</em></div><div className="row"><b>Critic</b>completed<em>1.2k tok</em></div></div>
 </div>
</section></div>

<div className="wrap"><section>
 <div className="head"><h2>The report fits what it found.</h2><p className="lead">A comparison becomes a table. Risks become a callout. A plan becomes steps. Sources stay numbered and linked.</p></div>
 <div id="sample-report" className="report"><div className="rp l"><h5>Report · sample</h5><div className="t">Two note-taking tools for a small team</div><p style={{ color: 'var(--muted)', margin: '0' }}>Alpha is cheaper at small scale and works offline. Beta is stronger on sharing and search as the team grows [1][2].</p>
  <h5>Findings</h5><table><tbody><tr><th>Feature</th><th>Alpha</th><th>Beta</th></tr><tr><td>Offline mode</td><td>Full</td><td>Read-only</td></tr><tr><td>Search</td><td>Title only</td><td>Full text</td></tr></tbody></table></div>
  <div className="rp"><h5>Risks and limitations</h5><div className="callout">Vendor prices may change. Re-check before committing [2].</div>
  <h5>Recommended next steps</h5><ol className="steps2"><li>Trial both tools for two weeks</li><li>Compare cost per active user</li></ol>
  <h5>Sources</h5><div className="src"><span>[1]</span>Alpha pricing page</div><div className="src"><span>[2]</span>Beta pricing page</div>
  <p className="small" style={{ marginTop: '16px' }}>Download as Markdown or JSON.</p></div></div>
</section></div>

<div className="wrap"><section>
 <div className="head"><h2>One run, five roles.</h2><p className="lead">The pipeline is fixed on purpose, so each result can be traced step by step.</p></div>
 <div className="flow"><div>Plan</div><div>Research</div><div>Analyse</div><div className="a">Critique</div><div>Write</div></div>
 <div className="small">The critic can send the draft back to the analyst. A human review can pause the run before the writer.</div>
</section></div>

<div className="wrap"><section><div className="cta2"><h2>Ask a hard question.<br />Watch it get challenged.</h2><Link className="btn" href="/tasks/new">Start a research task</Link></div></section></div>

<div className="wrap"><footer><div className="cols"><div><b style={{ color: 'var(--ink)', fontSize: '17px' }}>Critique</b><p style={{ maxWidth: '300px' }}>A research workbench: plan, search, analyse, challenge, approve.</p></div>
 <div><h6>Product</h6><Link href="/tasks/new">Start a task</Link><Link href="/">Dashboard</Link><Link href="/settings">Settings</Link></div>
 <div><h6>Project</h6><a href="https://github.com/Pskuntal1248/critique-agent">GitHub</a><a href={API_DOCS_URL}>API docs</a><Link href="/tasks/new">Report export</Link></div>
 <div><h6>Notes</h6><Link href="/settings">Bring your own key</Link><Link href="/settings">Free demo limits</Link><span style={{ display: 'block', margin: '6px 0' }}>Adapted from AgentForge</span></div></div></footer></div>

    </div>
  );
}
