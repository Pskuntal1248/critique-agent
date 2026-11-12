'use client';
import { defineComponent, createLibrary } from '@openuidev/react-lang';
import { z } from 'zod/v4';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const C = { ink:'#111', mute:'#666', line:'#e4e4e4', acc:'#88bdf2', soft:'#f4f9fe' };

const Md = ({ text }: { text: string }) => <div className="md"><ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown></div>;

export const Metric = defineComponent({
  name: 'Metric', description: 'One headline number with a label and optional note. Only use real figures from the research.',
  props: z.object({ label: z.string(), value: z.string(), note: z.string().optional() }),
  component: ({ props }) => (
    <div className="metric"><div className="ml">{props.label}</div><div className="mv">{props.value}</div>{props.note && <div className="mn">{props.note}</div>}</div>),
});
export const MetricRow = defineComponent({
  name: 'MetricRow', description: 'A row of 2-4 Metrics.',
  props: z.object({ items: z.array(Metric.ref) }),
  component: ({ props, renderNode }) => <div className="mrow">{renderNode(props.items)}</div>,
});
export const Callout = defineComponent({
  name: 'Callout', description: 'A short highlighted takeaway or warning. tone is "finding" or "risk".',
  props: z.object({ tone: z.enum(['finding','risk']), title: z.string(), body: z.string() }),
  component: ({ props }) => (
    <div className={'callout ' + props.tone}><b>{props.title}</b><Md text={props.body} /></div>),
});
export const Prose = defineComponent({
  name: 'Prose', description: 'A markdown paragraph block. Keep citation markers like [1].',
  props: z.object({ markdown: z.string() }),
  component: ({ props }) => <Md text={props.markdown} />,
});
export const Compare = defineComponent({
  name: 'Compare', description: 'A table comparing options. columns are headers, rows are arrays of cell strings. Use only when the report compares 2+ things.',
  props: z.object({ caption: z.string(), columns: z.array(z.string()), rows: z.array(z.array(z.string())) }),
  component: ({ props }) => (
    <figure className="tbl">{props.caption && <figcaption>{props.caption}</figcaption>}
      <div className="scroll"><table><thead><tr>{props.columns.map((c,i)=><th key={i}>{c}</th>)}</tr></thead>
      <tbody>{props.rows.map((r,i)=><tr key={i}>{r.map((c,j)=><td key={j}>{c}</td>)}</tr>)}</tbody></table></div></figure>),
});
export const Steps = defineComponent({
  name: 'Steps', description: 'An ordered list of steps or timeline items.',
  props: z.object({ title: z.string(), items: z.array(z.string()) }),
  component: ({ props }) => (<div>{props.title && <h3>{props.title}</h3>}<ol className="steps">{props.items.map((s,i)=><li key={i}>{s}</li>)}</ol></div>),
});
export const Section = defineComponent({
  name: 'Section', description: 'A titled section holding other blocks.',
  props: z.object({ heading: z.string(), blocks: z.array(z.union([Prose.ref, Compare.ref, MetricRow.ref, Callout.ref, Steps.ref])) }),
  component: ({ props, renderNode }) => (<section><h2>{props.heading}</h2>{renderNode(props.blocks)}</section>),
});
export const Source = defineComponent({
  name: 'Source', description: 'A cited source. n matches the [n] marker in the text.',
  props: z.object({ n: z.number(), title: z.string(), domain: z.string(), url: z.string() }),
  component: ({ props }) => (<li><span className="sn">[{props.n}]</span> {/^https?:\/\//i.test(props.url) ? <a href={props.url} target="_blank" rel="noreferrer">{props.title}</a> : <span>{props.title}</span>} <span className="sd">{props.domain}</span></li>),
});
export const Report = defineComponent({
  name: 'Report', description: 'Root. Title, one-paragraph summary, sections, then sources.',
  props: z.object({ title: z.string(), summary: z.string(), sections: z.array(Section.ref), sources: z.array(Source.ref) }),
  component: ({ props, renderNode }) => (
    <article className="report">
      <h1>{props.title}</h1>{props.summary && <div className="sum"><Md text={props.summary} /></div>}
      {renderNode(props.sections)}
      <section><h2>Sources</h2><ul className="src">{renderNode(props.sources)}</ul></section>
    </article>),
});

export const reportLibrary = createLibrary({ root: 'Report', components: [Report, Section, Prose, Compare, MetricRow, Metric, Callout, Steps, Source] });
