// app/layout.tsx
import type { Metadata } from 'next';
import './globals.css';
import Navbar from '@/components/Navbar';

export const metadata: Metadata = {
  title: 'PackGuard v2.0',
  description: 'Agentic AI for Packaging Reliability Risk Identification',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-950 text-white flex flex-col">
        <Navbar />
        <main className="flex-1 p-6">{children}</main>
      </body>
    </html>
  );
}