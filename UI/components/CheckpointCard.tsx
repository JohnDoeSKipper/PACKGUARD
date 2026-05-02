// components/CheckpointCard.tsx
'use client';
import { useState } from 'react';
import { CheckCircle, AlertTriangle, XCircle, Clock, Loader2, ChevronDown, ChevronRight } from 'lucide-react';
import { CheckpointResult } from '@/lib/types';

const STEP_ICONS: Record<string, string> = {
  'Dicing': '✂️', 'Die Attach': '🔩', 'Wire Bond': '🔗',
  'Molding': '🧱', 'Reflow': '🔥', 'Test': '🧪', 'Final Gate': '🚦',
};

export default function CheckpointCard({ checkpoint }: { checkpoint: CheckpointResult }) {
  const [open, setOpen] = useState(false);
  const { status, name, step, reasons, tools_run, cost_avoided, debate_triggered } = checkpoint;

  const statusConfig = {
    pass: { icon: <CheckCircle size={20} />, colour: 'text-green-400', bg: 'bg-green-400/10 border-green-800', badge: 'PASS', badgeBg: 'bg-green-900 text-green-300' },
    flag: { icon: <AlertTriangle size={20} />, colour: 'text-yellow-400', bg: 'bg-yellow-400/10 border-yellow-800', badge: 'FLAG', badgeBg: 'bg-yellow-900 text-yellow-300' },
    kill: { icon: <XCircle size={20} />, colour: 'text-red-400', bg: 'bg-red-400/10 border-red-800', badge: 'KILL', badgeBg: 'bg-red-900 text-red-300' },
    pending: { icon: <Clock size={20} />, colour: 'text-gray-600', bg: 'bg-gray-900 border-gray-800', badge: '—', badgeBg: 'bg-gray-800 text-gray-500' },
    running: { icon: <Loader2 size={20} className="animate-spin" />, colour: 'text-blue-400', bg: 'bg-blue-400/10 border-blue-800', badge: '...', badgeBg: 'bg-blue-900 text-blue-300' },
  };

  const cfg = statusConfig[status];

  return (
    <div className={`border rounded-xl transition-all ${cfg.bg}`}>
      <button onClick={() => setOpen(o => !o)} className="w-full flex items-center gap-4 p-4 text-left">
        <span className="text-xl w-6 text-center">{STEP_ICONS[name]}</span>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Step {step}</span>
            <span className={`font-semibold text-sm ${status === 'pending' ? 'text-gray-600' : 'text-white'}`}>{name}</span>
            {debate_triggered && (
              <span className="text-xs bg-purple-900 text-purple-300 px-2 py-0.5 rounded-full">DEBATE</span>
            )}
          </div>
          {status !== 'pending' && status !== 'running' && (
            <p className="text-xs text-gray-400 mt-0.5 truncate max-w-lg">{reasons[0]}</p>
          )}
        </div>
        <div className={`text-xs font-bold px-2 py-1 rounded ${cfg.badgeBg}`}>{cfg.badge}</div>
        {cost_avoided > 0 && (
          <div className="text-xs font-semibold text-green-400">+${cost_avoided.toLocaleString()} saved</div>
        )}
        <span className={`${cfg.colour}`}>{cfg.icon}</span>
        {status !== 'pending' && (open ? <ChevronDown size={16} className="text-gray-500" /> : <ChevronRight size={16} className="text-gray-500" />)}
      </button>

      {open && status !== 'pending' && status !== 'running' && (
        <div className="px-4 pb-4 space-y-3 border-t border-gray-800 pt-3">
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Tools Run</p>
            <div className="flex flex-wrap gap-1">
              {tools_run.map(t => (
                <span key={t} className="text-xs bg-gray-800 text-gray-300 px-2 py-0.5 rounded">{t}</span>
              ))}
            </div>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Findings</p>
            <ul className="space-y-1">
              {reasons.map((r, i) => <li key={i} className="text-sm text-gray-300 flex gap-2"><span className="text-gray-600">›</span>{r}</li>)}
            </ul>
          </div>
          {checkpoint.debate_log && checkpoint.debate_log.length > 0 && (
            <div className="bg-purple-950 border border-purple-800 rounded-lg p-3">
              <p className="text-xs text-purple-300 font-semibold uppercase tracking-wider mb-2">Debate Protocol Fired — Rule {checkpoint.debate_log[0].rule_number}: {checkpoint.debate_log[0].rule_name}</p>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <p className="text-gray-400 font-medium">{checkpoint.debate_log[0].tool_a}</p>
                  <p className="text-gray-300 mt-0.5">{checkpoint.debate_log[0].tool_a_says}</p>
                </div>
                <div>
                  <p className="text-gray-400 font-medium">{checkpoint.debate_log[0].tool_b}</p>
                  <p className="text-gray-300 mt-0.5">{checkpoint.debate_log[0].tool_b_says}</p>
                </div>
              </div>
              <p className="text-purple-300 text-xs mt-2">Winner: <strong>{checkpoint.debate_log[0].winner}</strong> — {checkpoint.debate_log[0].reason}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}