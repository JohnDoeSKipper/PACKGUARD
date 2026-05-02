// app/report/page.tsx
'use client';
import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { getFinalReport } from '@/lib/api';
import { FinalReport } from '@/lib/types';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, ReferenceLine, Cell } from 'recharts';
import { Download, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';

function ReportPage() {
  const params = useSearchParams();
  const lot_id = params.get('lot_id') || 'LOT-2026-001';
  const [report, setReport] = useState<FinalReport | null>(null);

  useEffect(() => { getFinalReport(lot_id).then(setReport); }, [lot_id]);

  if (!report) return <div className="text-gray-400">Generating report...</div>;

  const radarData = report.failure_modes.map(m => ({
    subject: m.name.replace(' ', '\n').split(' ').slice(0, 2).join(' '),
    value: Math.round(m.probability * 1_000_000),
  }));

  const barData = report.failure_modes.map(m => ({
    name: m.name.split(' ').slice(0, 2).join(' '),
    dppm: Math.round(m.probability * 1_000_000),
    threshold: m.threshold_dppm,
  }));

  const DecisionBanner = () => {
    if (report.overall_decision === 'ship')
      return <div className="bg-green-700 rounded-xl p-4 flex items-center gap-3"><CheckCircle size={24} /><div><p className="font-bold text-lg">LOT APPROVED FOR SHIPMENT</p><p className="text-green-200 text-sm">All failure modes within threshold. Cleared for shipping.</p></div></div>;
    if (report.overall_decision === 'hold')
      return <div className="bg-yellow-700 rounded-xl p-4 flex items-center gap-3"><AlertTriangle size={24} /><div><p className="font-bold text-lg">LOT ON HOLD — ADDITIONAL INSPECTION REQUIRED</p><p className="text-yellow-200 text-sm">One or more findings require engineer review before shipping.</p></div></div>;
    return <div className="bg-red-700 rounded-xl p-4 flex items-center gap-3"><XCircle size={24} /><div><p className="font-bold text-lg">LOT REJECTED — DO NOT SHIP</p><p className="text-red-200 text-sm">Failure probability exceeds threshold. Reject or rework.</p></div></div>;
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold">Final Report</h1><p className="text-gray-500 text-sm mt-0.5">Lot: {lot_id}</p></div>
        <button onClick={() => window.open(report.pdf_url, '_blank')}
          className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm transition-colors">
          <Download size={16} /> Download PDF
        </button>
      </div>

      <DecisionBanner />

      {/* Lifetime */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex items-center justify-between">
        <div>
          <p className="text-gray-400 text-sm">Predicted Lifetime</p>
          <p className="text-4xl font-bold text-white mt-1">{report.predicted_lifetime_years.toFixed(1)} <span className="text-xl text-gray-400">years</span></p>
          <p className="text-sm text-gray-500 mt-1">90% CI: {report.confidence_interval[0]} – {report.confidence_interval[1]} years</p>
        </div>
        <div className="text-right">
          <p className="text-gray-400 text-sm">Overall P(fail)</p>
          <p className="text-2xl font-bold text-white mt-1">{(report.overall_probability_of_failure * 1_000_000).toFixed(1)} <span className="text-base text-gray-400">DPPM</span></p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p className="text-sm text-gray-400 mb-3">Failure Mode Risk Radar</p>
          <ResponsiveContainer width="100%" height={220}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#374151" />
              <PolarAngleAxis dataKey="subject" tick={{ fill: '#9ca3af', fontSize: 10 }} />
              <Radar dataKey="value" stroke="#60a5fa" fill="#60a5fa" fillOpacity={0.25} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p className="text-sm text-gray-400 mb-3">Failure Mode DPPM vs Threshold</p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={barData} layout="vertical" margin={{ left: 80 }}>
              <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 10 }} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#9ca3af', fontSize: 10 }} width={80} />
              <Tooltip contentStyle={{ background: '#111827', border: '1px solid #374151', color: '#fff' }} />
              <ReferenceLine x={10} stroke="#ef4444" strokeDasharray="4 4" label={{ value: 'Threshold', fill: '#ef4444', fontSize: 10 }} />
              <Bar dataKey="dppm" radius={[0, 4, 4, 0]}>
                {barData.map((d, i) => (
                  <Cell key={i} fill={d.dppm > d.threshold ? '#ef4444' : d.dppm > d.threshold * 0.7 ? '#f59e0b' : '#22c55e'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Narrative */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <p className="text-sm text-gray-400 uppercase tracking-wider mb-3">Engineer Summary</p>
        <p className="text-gray-300 leading-relaxed text-sm">{report.narrative}</p>
      </div>

      {/* Debate log */}
      {report.debate_log.length > 0 && (
        <div className="bg-purple-950 border border-purple-800 rounded-xl p-5">
          <p className="text-sm text-purple-300 uppercase tracking-wider mb-3">Debate Protocol Log ({report.debate_log.length} conflict{report.debate_log.length > 1 ? 's' : ''} resolved)</p>
          {report.debate_log.map((d, i) => (
            <div key={i} className="text-sm text-gray-300 space-y-1">
              <p className="font-semibold text-purple-300">Rule {d.rule_number}: {d.rule_name}</p>
              <p>{d.tool_a}: {d.tool_a_says}</p>
              <p>{d.tool_b}: {d.tool_b_says}</p>
              <p className="text-purple-300">→ Winner: {d.winner} — {d.reason}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Page() {
  return <Suspense fallback={<div className="text-gray-400 p-6">Loading report...</div>}><ReportPage /></Suspense>;
}