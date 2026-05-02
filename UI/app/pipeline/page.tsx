// app/pipeline/page.tsx
'use client';
import { useEffect, useState, useRef } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Suspense } from 'react';
import { getLotState } from '@/lib/api';
import { LotState } from '@/lib/types';
import CheckpointCard from '@/components/CheckpointCard';
import { ArrowRight, TrendingUp } from 'lucide-react';

function PipelinePage() {
  const params = useSearchParams();
  const router = useRouter();
  const lot_id = params.get('lot_id') || 'LOT-2026-001';
  const [lot, setLot] = useState<LotState | null>(null);
  const [displayedCost, setDisplayedCost] = useState(0);
  const costRef = useRef(0);

  useEffect(() => {
    getLotState(lot_id).then(data => {
      // Animate checkpoints appearing one by one for visual effect
      let i = 0;
      const reveal = setInterval(() => {
        i++;
        setLot({ ...data, checkpoints: data.checkpoints.slice(0, i).map((c, idx) => idx < i - 1 ? c : { ...c, status: i < data.checkpoints.length ? c.status : c.status }) });
        if (i >= data.checkpoints.length) {
          clearInterval(reveal);
          setLot(data);
        }
      }, 600);
    });
  }, [lot_id]);

  // Animate cost counter
  useEffect(() => {
    if (!lot) return;
    const target = lot.total_cost_avoided;
    if (target <= costRef.current) return;
    const step = Math.ceil((target - costRef.current) / 30);
    const timer = setInterval(() => {
      costRef.current = Math.min(costRef.current + step, target);
      setDisplayedCost(costRef.current);
      if (costRef.current >= target) clearInterval(timer);
    }, 30);
    return () => clearInterval(timer);
  }, [lot?.total_cost_avoided]);

  const done = lot?.overall_decision !== 'in_progress';

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Live Pipeline</h1>
          <p className="text-gray-500 text-sm mt-0.5">Lot: {lot_id}</p>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl px-6 py-3 text-center">
          <div className="flex items-center gap-2 text-green-400 font-bold text-2xl tabular-nums">
            <TrendingUp size={20} />
            ${displayedCost.toLocaleString()}
          </div>
          <p className="text-xs text-gray-500 mt-0.5">Waste Prevented This Lot</p>
        </div>
      </div>

      {!lot && (
        <div className="flex items-center gap-3 text-gray-400 py-8">
          <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
          Loading lot data...
        </div>
      )}

      <div className="space-y-3">
        {(lot?.checkpoints || []).map(cp => (
          <CheckpointCard key={cp.step} checkpoint={cp} />
        ))}
      </div>

      {done && lot && (
        <div className="pt-4">
          <button onClick={() => router.push(`/report?lot_id=${lot_id}`)}
            className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-3 rounded-xl flex items-center justify-center gap-2 transition-colors">
            View Full Report <ArrowRight size={18} />
          </button>
          {lot.forward_sim && (
            <button onClick={() => router.push(`/simulation?lot_id=${lot_id}`)}
              className="w-full mt-2 border border-red-700 text-red-400 hover:bg-red-900/20 font-semibold py-3 rounded-xl flex items-center justify-center gap-2 transition-colors">
              View Crack Simulation
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default function Page() {
  return <Suspense fallback={<div className="text-gray-400 p-6">Loading...</div>}><PipelinePage /></Suspense>;
}