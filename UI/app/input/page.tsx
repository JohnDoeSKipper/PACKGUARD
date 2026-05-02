// app/input/page.tsx
'use client';
import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Upload, FlaskConical, Zap } from 'lucide-react';
import { analyzeLot, loadDemoScenario } from '@/lib/api';
import { PackageType, Application } from '@/lib/types';

const PACKAGE_TYPES: PackageType[] = ['BGA', 'QFN', 'QFP', 'CSP', 'Flip-Chip', 'SiP'];
const APPLICATIONS: { value: Application; label: string }[] = [
  { value: 'automotive', label: 'Automotive (AEC-Q100) — target < 10 DPPM' },
  { value: 'server', label: 'Server / Datacenter — target < 100 DPPM' },
  { value: 'consumer', label: 'Consumer (Phones) — target < 1,000 DPPM' },
  { value: 'industrial', label: 'Industrial — target < 50 DPPM' },
];

export default function InputPage() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const [packageType, setPackageType] = useState<PackageType>('BGA');
  const [application, setApplication] = useState<Application>('automotive');
  const [loading, setLoading] = useState(false);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    setFiles(prev => [...prev, ...Array.from(e.dataTransfer.files)]);
  }

  async function handleAnalyze() {
    setLoading(true);
    const { lot_id } = await analyzeLot(files, packageType, application);
    router.push(`/pipeline?lot_id=${lot_id}`);
  }

  async function handleDemo(scenario: 'clean' | 'early_kill' | 'debate') {
    setLoading(true);
    const { lot_id } = await loadDemoScenario(scenario);
    router.push(`/pipeline?lot_id=${lot_id}`);
  }

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Analyze a Lot</h1>
        <p className="text-gray-400 mt-1 text-sm">Upload lot data and select configuration to begin the 7-checkpoint analysis.</p>
      </div>

      {/* File Upload */}
      <div
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
          dragging ? 'border-blue-400 bg-blue-400/10' : 'border-gray-700 hover:border-gray-500'
        }`}
      >
        <Upload className="mx-auto mb-3 text-gray-400" size={32} />
        <p className="text-white font-medium">Drop files here or click to upload</p>
        <p className="text-gray-500 text-sm mt-1">Accepts: .png .jpg .csv .json (X-ray images, reflow CSVs, material specs)</p>
        <input ref={fileRef} type="file" multiple accept=".png,.jpg,.jpeg,.csv,.json" className="hidden"
          onChange={e => setFiles(prev => [...prev, ...Array.from(e.target.files || [])])} />
      </div>

      {files.length > 0 && (
        <div className="bg-gray-900 rounded-lg p-4 space-y-1">
          {files.map((f, i) => (
            <div key={i} className="flex items-center justify-between text-sm">
              <span className="text-gray-300">{f.name}</span>
              <span className="text-gray-500">{(f.size / 1024).toFixed(1)} KB</span>
            </div>
          ))}
        </div>
      )}

      {/* Config */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm text-gray-400 mb-2">Package Type</label>
          <select value={packageType} onChange={e => setPackageType(e.target.value as PackageType)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500">
            {PACKAGE_TYPES.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm text-gray-400 mb-2">Target Application</label>
          <select value={application} onChange={e => setApplication(e.target.value as Application)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500">
            {APPLICATIONS.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
          </select>
        </div>
      </div>

      <button onClick={handleAnalyze} disabled={loading || files.length === 0}
        className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2">
        {loading ? (
          <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> Analyzing...</>
        ) : (
          <><FlaskConical size={18} /> Analyze Lot</>
        )}
      </button>

      {/* Demo Scenarios */}
      <div className="border border-gray-800 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Zap size={16} className="text-yellow-400" />
          <span className="text-sm font-semibold text-gray-300">Demo Scenarios</span>
          <span className="text-xs text-gray-600 ml-auto">No file upload needed</span>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {[
            { key: 'clean' as const, label: 'Clean Lot', desc: 'All 7 checkpoints pass', colour: 'border-green-700 hover:border-green-500 text-green-400' },
            { key: 'early_kill' as const, label: 'Early Kill', desc: 'Crack → KILL at Step 1', colour: 'border-red-700 hover:border-red-500 text-red-400' },
            { key: 'debate' as const, label: 'Debate Trigger', desc: 'Vision vs SPC conflict', colour: 'border-yellow-700 hover:border-yellow-500 text-yellow-400' },
          ].map(s => (
            <button key={s.key} onClick={() => handleDemo(s.key)} disabled={loading}
              className={`border rounded-lg p-3 text-left transition-colors bg-gray-950 ${s.colour}`}>
              <div className="font-medium text-sm">{s.label}</div>
              <div className="text-xs text-gray-500 mt-0.5">{s.desc}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}