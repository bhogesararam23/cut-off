import { C } from '../../lib/content.ts';

/** Simple diagram: forest gives many bounces (strong HV), a bare scar gives one bounce (weak HV). */
function Diagram() {
  return (
    <svg
      viewBox="0 0 360 170"
      role="img"
      aria-label={`${C.why.diagramForest}. ${C.why.diagramScar}.`}
      className="w-full rounded border border-slate-200 bg-white"
    >
      <defs>
        <marker id="why-arrow" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">
          <path d="M0 0 L6 3 L0 6 z" fill="#2563eb" />
        </marker>
      </defs>
      <g fontSize="11" fill="#0f172a">
        <rect x="10" y="130" width="160" height="20" fill="#bbf7d0" />
        {[40, 90, 140].map((x) => (
          <g key={x}>
            <rect x={x - 3} y="105" width="6" height="25" fill="#78350f" />
            <circle cx={x} cy="95" r="16" fill="#16a34a" />
          </g>
        ))}
        <path d="M60 10 L90 80 L65 60 L120 85 L100 20" fill="none" stroke="#2563eb" strokeWidth="2" strokeDasharray="4 3" />
        <path d="M115 85 L150 40" fill="none" stroke="#2563eb" strokeWidth="3" markerEnd="url(#why-arrow)" />
        <text x="10" y="165">{C.why.diagramForest}</text>
        <rect x="190" y="130" width="160" height="20" fill="#d6b98c" />
        <path d="M250 10 L270 128" fill="none" stroke="#2563eb" strokeWidth="2" strokeDasharray="4 3" />
        <path d="M270 128 L292 90" fill="none" stroke="#2563eb" strokeWidth="1" markerEnd="url(#why-arrow)" />
        <text x="190" y="165">{C.why.diagramScar}</text>
      </g>
    </svg>
  );
}

export function WhyRadar() {
  return (
    <section aria-labelledby="why-h" className="space-y-3 text-[15px]">
      <h2 id="why-h" className="text-lg font-semibold">{C.why.heading}</h2>
      <p>{C.why.p1}</p>
      <p>{C.why.p2}</p>
      <p>{C.why.p3}</p>
      <Diagram />
      <blockquote className="border-l-4 border-slate-300 pl-3 text-slate-700">{C.why.quote}</blockquote>
    </section>
  );
}
