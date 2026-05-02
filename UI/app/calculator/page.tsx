// app/calculator/page.tsx
'use client';
import { useState } from 'react';
import { Calculator } from 'lucide-react';

interface Inputs { annualLots: string; lotSize: string; escapeRate: string; fieldFailureCost: string; deploymentCost: string; }

export default function CalculatorPage() {
  const [inputs, setInputs] = useState<Inputs>({ annualLots: '10000', lotSize: '4000', escapeRate: '0.5', fieldFailureCost: '10000', deploymentCost: '500000' });
  const [results, setResults] = useState<{ leakage: number; savings: number; net: number; roi: number } | null>(null);

  function calc() {
    const lots = parseFloat(inputs.annualLots), size = parseFloat(inputs.lotSize);
    const rate = parseFloat(inputs.escapeRate) / 100, ffc = parseFloat(inputs.fieldFailureCost);
    const deploy = parseFloat(inputs.deploymentCost);
    const leakage = lots * size * rate * ffc;
    const savings = leakage * 0.80;
    const net = savings - deploy;
    const roi = (net / deploy) * 100;
    setResults({ leakage, savings, net, roi });
  }

  const fmt = (n: number) => n >= 1_000_000 ? `$${(n / 1_000_000).toFixed(2)}M` : `$${Math.round(n).toLocaleString()}`;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Cost-of-Quality Calculator</h1>
        <p className="text-gray-400 text-sm mt-1">Quantify the financial case for inline QC. Every input is editable.</p>
      </div>
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
        {([
          ['Annual lot volume (lots/year)', 'annualLots', 'Typical mid-size fab: 8,000–15,000'],
          ['Average lot size (chips/lot)', 'lotSize', 'Typical: 3,000–5,000'],
          ['Current escape rate (%)', 'escapeRate', 'Defective lots that ship undetected. Industry range: 0.1–2%'],
          ['Field failure cost per chip ($)', 'fieldFailureCost', 'Automotive recall: ~$10,000. Consumer: ~$50. Source: IPC cost models'],
          ['PackGuard deployment cost ($/year)', 'deploymentCost', 'SaaS estimate including infrastructure'],
        ] as [string, keyof Inputs, string][]).map(([label, key, hint]) => (
          <div key={key}>
            <label className="block text-sm text-gray-300 mb-1">{label}</label>
            <input type="number" value={inputs[key]} onChange={e => setInputs(p => ({ ...p, [key]: e.target.value }))}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
            <p className="text-xs text-gray-600 mt-0.5">{hint}</p>
          </div>
        ))}
        <button onClick={calc} className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-3 rounded-xl flex items-center justify-center gap-2 transition-colors">
          <Calculator size={18} /> Calculate ROI
        </button>
      </div>

      {results && (
        <div className="space-y-3">
          <div className="bg-red-950 border border-red-800 rounded-xl p-5">
            <p className="text-xs text-red-400 uppercase tracking-wider">Current Annual Leakage (without PackGuard)</p>
            <p className="text-3xl font-bold text-white mt-1">{fmt(results.leakage)}</p>
            <p className="text-xs text-gray-500 mt-1">= {inputs.annualLots} lots × {inputs.lotSize} chips × {inputs.escapeRate}% escape × ${parseFloat(inputs.fieldFailureCost).toLocaleString()} field failure</p>
          </div>
          <div className="bg-green-950 border border-green-800 rounded-xl p-5">
            <p className="text-xs text-green-400 uppercase tracking-wider">Annual Savings with PackGuard (80% escape reduction — conservative)</p>
            <p className="text-3xl font-bold text-white mt-1">{fmt(results.savings)}</p>
          </div>
          <div className="bg-blue-950 border border-blue-800 rounded-xl p-5">
            <p className="text-xs text-blue-400 uppercase tracking-wider">Net Annual ROI (savings minus deployment)</p>
            <p className="text-3xl font-bold text-white mt-1">{fmt(results.net)}</p>
            <p className="text-2xl font-bold text-blue-400 mt-1">{results.roi.toFixed(0)}% return</p>
          </div>
          <p className="text-xs text-gray-600">Assumptions: 80% escape reduction is conservative; actual reduction depends on lot profile and calibration. Field failure cost source: IPC-7711 cost models. All inputs editable above.</p>
        </div>
      )}
    </div>
  );
}