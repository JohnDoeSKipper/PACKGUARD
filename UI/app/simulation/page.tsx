// app/simulation/page.tsx
'use client';
import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { getLotState } from '@/lib/api';
import { ForwardSimResult } from '@/lib/types';

function SimPage() {
  const params = useSearchParams();
  const lot_id = params.get('lot_id') || 'LOT-2026-002';
  const [sim, setSim] = useState<ForwardSimResult | null>(null);

  useEffect(() => { getLotState(lot_id).then(d => setSim(d.forward_sim || null)); }, [lot_id]);

  if (!sim) return <div className="text-gray-400">Loading simulation...</div>;

  const W = 700, H = 260, PAD = 60;
  const maxCrack = Math.max(...sim.steps.map(s => s.crack_length_mm), sim.critical_threshold_mm) * 1.2;
  const xScale = (i: number) => PAD + (i / (sim.steps.length - 1)) * (W - PAD * 2);
  const yScale = (v: number) => H - PAD - (v / maxCrack) * (H - PAD * 2);
  const points = sim.steps.map((s, i) => `${xScale(i)},${yScale(s.crack_length_mm)}`).join(' ');
  const threshY = yScale(sim.critical_threshold_mm);
  const failIdx = sim.steps.findIndex(s => s.crack_length_mm >= sim.critical_threshold_mm);
  const failX = failIdx >= 0 ? xScale(failIdx) : null;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Forward Simulation</h1>
        <p className="text-gray-400 text-sm mt-1">Lot: {lot_id} — predicting crack growth across remaining process steps</p>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 280 }}>
          {/* Grid lines */}
          {[0.5, 1.0, 1.5, 2.0, 2.5].map(v => (
            <g key={v}>
              <line x1={PAD} y1={yScale(v)} x2={W - PAD} y2={yScale(v)} stroke="#374151" strokeDasharray="4 4" strokeWidth={1} />
              <text x={PAD - 8} y={yScale(v) + 4} textAnchor="end" fill="#6b7280" fontSize={10}>{v}mm</text>
            </g>
          ))}
          {/* Critical threshold */}
          <line x1={PAD} y1={threshY} x2={W - PAD} y2={threshY} stroke="#ef4444" strokeDasharray="6 3" strokeWidth={2} />
          <text x={W - PAD + 4} y={threshY + 4} fill="#ef4444" fontSize={10}>Critical</text>
          {/* Crack growth line */}
          <polyline points={points} fill="none" stroke="#60a5fa" strokeWidth={3} strokeLinejoin="round" />
          {/* Data points */}
          {sim.steps.map((s, i) => (
            <circle key={i} cx={xScale(i)} cy={yScale(s.crack_length_mm)} r={5}
              fill={s.crack_length_mm >= sim.critical_threshold_mm ? '#ef4444' : '#60a5fa'} />
          ))}
          {/* Failure vertical line */}
          {failX && (
            <>
              <line x1={failX} y1={PAD} x2={failX} y2={H - PAD} stroke="#ef4444" strokeWidth={2} strokeDasharray="5 3" />
              <text x={failX} y={PAD - 6} textAnchor="middle" fill="#ef4444" fontSize={11} fontWeight="bold">Fracture</text>
            </>
          )}
          {/* Step labels */}
          {sim.steps.map((s, i) => (
            <text key={i} x={xScale(i)} y={H - 10} textAnchor="middle" fill="#9ca3af" fontSize={10}>{s.step_name.replace(' ', '\n')}</text>
          ))}
          {/* Y axis label */}
          <text x={16} y={H / 2} textAnchor="middle" fill="#6b7280" fontSize={10} transform={`rotate(-90, 16, ${H / 2})`}>Crack Length</text>
        </svg>
      </div>

      <div className="bg-red-950 border border-red-800 rounded-xl p-5">
        <p className="text-red-300 font-semibold text-sm uppercase tracking-wider mb-2">Simulation Result</p>
        <p className="text-white leading-relaxed">
          This die has a <strong className="text-red-400">{sim.initial_crack_mm} mm crack</strong> after dicing.{' '}
          {sim.failure_reason}{' '}
          Killing at Step 1 saves <strong className="text-green-400">${sim.cost_saved.toLocaleString()}</strong> in downstream processing.
        </p>
        <div className="mt-4 space-y-1">
          {sim.steps.map((s, i) => (
            <div key={i} className="flex items-center gap-3 text-sm">
              <span className="text-gray-500 w-5 text-right">{i + 1}</span>
              <span className="text-gray-400 w-32">{s.step_name}</span>
              <div className="flex-1 bg-gray-800 rounded-full h-2">
                <div className={`h-2 rounded-full transition-all ${s.crack_length_mm >= sim.critical_threshold_mm ? 'bg-red-500' : 'bg-blue-500'}`}
                  style={{ width: `${Math.min(100, (s.crack_length_mm / maxCrack) * 100)}%` }} />
              </div>
              <span className={`w-16 text-right font-mono text-xs ${s.crack_length_mm >= sim.critical_threshold_mm ? 'text-red-400' : 'text-gray-400'}`}>
                {s.crack_length_mm} mm
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function Page() {
  return <Suspense fallback={<div className="text-gray-400 p-6">Loading...</div>}><SimPage /></Suspense>;
}