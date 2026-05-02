// components/Navbar.tsx
'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const links = [
  { href: '/input', label: 'New Lot' },
  { href: '/pipeline', label: 'Pipeline' },
  { href: '/report', label: 'Report' },
  { href: '/knowledge', label: 'Knowledge' },
  { href: '/calculator', label: 'ROI Calculator' },
];

export default function Navbar() {
  const path = usePathname();
  return (
    <nav className="w-full bg-gray-950 border-b border-gray-800 px-6 py-3 flex items-center gap-8">
      <span className="text-white font-bold text-lg tracking-tight">
        Pack<span className="text-blue-400">Guard</span>
        <span className="ml-2 text-xs text-gray-500 font-normal">v2.0</span>
      </span>
      <div className="flex gap-6">
        {links.map(l => (
          <Link
            key={l.href}
            href={l.href}
            className={`text-sm transition-colors ${
              path === l.href
                ? 'text-blue-400 border-b-2 border-blue-400 pb-0.5'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            {l.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}