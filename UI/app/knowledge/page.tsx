// app/knowledge/page.tsx
'use client';
import { useState } from 'react';
import { ChevronRight, ChevronDown } from 'lucide-react';

interface TreeNode { id: string; label: string; type: 'mode' | 'cause' | 'model' | 'case'; detail?: string; children?: TreeNode[]; }

const TREE: TreeNode[] = [
  { id: 'tf', label: 'Solder Joint Thermal Fatigue', type: 'mode', detail: 'The dominant failure mode for surface-mount packages under temperature cycling.', children: [
    { id: 'tf-c', label: 'Root Cause: CTE mismatch under thermal cycling', type: 'cause', detail: 'Silicon (CTE 2.6 ppm/°C) vs FR4 PCB (CTE 18 ppm/°C). Shear stress accumulates at solder joints every cycle.' },
    { id: 'tf-m', label: 'Physics Model: Coffin-Manson (Nf = C × ΔT⁻ⁿ)', type: 'model', detail: 'n ≈ 2.0 for SAC305 solder. C is material constant. ΔT is the thermal swing in service. Source: JEDEC JESD22-A104.' },
    { id: 'tf-h', label: 'Case: BGA lot, automotive, 2024 — predicted 1,200 cycles, failed at 1,050', type: 'case', detail: 'Root cause: underfill delamination accelerated crack propagation. Model updated with interaction term.' },
  ]},
  { id: 'em', label: 'Electromigration', type: 'mode', detail: 'High current density drives metal atoms in one direction, forming voids that eventually open-circuit the interconnect.', children: [
    { id: 'em-c', label: 'Root Cause: High current density in fine-pitch interconnects', type: 'cause', detail: 'Current density J > 10⁶ A/cm² accelerates ion migration. Critical for advanced nodes with narrow metal lines.' },
    { id: 'em-m', label: "Physics Model: Black's Equation (MTTF = A × J⁻ⁿ × exp(Ea/kT))", type: 'model', detail: 'n ≈ 2, Ea ≈ 0.7 eV for copper interconnects. Source: Black (1969), IEEE Transactions.' },
    { id: 'em-h', label: 'Case: Server DRAM lot, 2023 — flagged by Black model at 8.1 yr MTTF vs 7 yr spec', type: 'case', detail: 'Customer confirmed failure pattern at 6.5 yr in field. Model prediction within 25%.' },
  ]},
  { id: 'hc', label: 'Humidity-Driven Corrosion', type: 'mode', detail: 'Moisture ingress corrodes metal lines and bond pads, especially in tropical/coastal environments.', children: [
    { id: 'hc-c', label: 'Root Cause: Moisture diffusion through mold compound', type: 'cause', detail: 'EMC absorbs moisture during storage and assembly. Under bias, electrochemical corrosion accelerates.' },
    { id: 'hc-m', label: "Physics Model: Peck's Model (TTF ∝ RH⁻ⁿ × exp(Ea/kT))", type: 'model', detail: 'n ≈ 2.7 for epoxy packages. Ea ≈ 0.9 eV. Source: Peck (1986), IRPS.' },
    { id: 'hc-h', label: 'Case: Industrial lot, SE Asia deployment — Peck predicted 4.8 yr, observed 4.2 yr', type: 'case', detail: 'Consistent with model. Now applying 15% safety margin for tropical deployments.' },
  ]},
  { id: 'imc', label: 'Wire Bond IMC Failure', type: 'mode', detail: 'Brittle intermetallic compound layer grows at the Au-Al or Cu-Al bond interface, leading to lifted bonds under thermal cycling.', children: [
    { id: 'imc-c', label: 'Root Cause: Kirkendall void formation at Cu-Al interface', type: 'cause', detail: 'Differential diffusion rates of Cu and Al create voids. Above 5 µm IMC, bonds become mechanically brittle.' },
    { id: 'imc-m', label: 'Physics Model: Arrhenius IMC Growth (x = √(D₀ × exp(-Ea/kT) × t))', type: 'model', detail: 'D₀ and Ea from published tables for Cu-Al and Au-Al systems. Threshold: 5 µm. Source: JEDEC JESD22-A110.' },
  ]},
  { id: 'pop', label: 'Popcorn Cracking', type: 'mode', detail: 'Moisture absorbed by the mold compound vaporises rapidly at reflow temperatures, causing internal delamination and audible cracking.', children: [
    { id: 'pop-c', label: 'Root Cause: Trapped moisture expanding at 245°C', type: 'cause', detail: 'J-STD-020 MSL rating defines the safe bake-and-ship window. Exceeding it leads to popcorn cracking.' },
    { id: 'pop-m', label: 'Physics Model: Ideal Gas Law + vapour pressure at reflow temperature', type: 'model', detail: 'Gas volume expands ~74% from 25°C to 245°C (PV=nRT). Stress exceeds EMC adhesion strength if moisture exceeds MSL limit.' },
  ]},
];

function TreeItem({ node, depth }: { node: TreeNode; depth: number }) {
  const [open, setOpen] = useState(false);
  const typeColour = { mode: 'text-blue-400', cause: 'text-yellow-400', model: 'text-green-400', case: 'text-purple-400' };
  const typeBadge = { mode: 'Failure Mode', cause: 'Root Cause', model: 'Physics Model', case: 'Historical Case' };
  return (
    <div style={{ marginLeft: depth * 20 }}>
      <button onClick={() => setOpen(o => !o)} className="flex items-start gap-2 py-2 px-3 rounded-lg hover:bg-gray-800 w-full text-left group transition-colors">
        <span className="mt-0.5 text-gray-600 flex-shrink-0">{node.children ? (open ? <ChevronDown size={14} /> : <ChevronRight size={14} />) : <span className="w-3.5 block" />}</span>
        <div className="flex-1 min-w-0">
          <span className={`text-xs font-medium ${typeColour[node.type]} mr-2`}>[{typeBadge[node.type]}]</span>
          <span className="text-sm text-gray-200">{node.label}</span>
          {node.detail && open && <p className="text-xs text-gray-400 mt-1 leading-relaxed">{node.detail}</p>}
        </div>
      </button>
      {open && node.children?.map(child => <TreeItem key={child.id} node={child} depth={depth + 1} />)}
    </div>
  );
}

export default function KnowledgePage() {
  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Knowledge Tree</h1>
        <p className="text-gray-400 text-sm mt-1">Failure modes → root causes → physics models → historical cases. Click any node to expand.</p>
      </div>
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
        {TREE.map(node => <TreeItem key={node.id} node={node} depth={0} />)}
      </div>
    </div>
  );
}