/**
 * Root layout — sets up fonts, Tailwind, and the React Query provider.
 */

import type { Metadata } from 'next';
import { Inter, Crimson_Text } from 'next/font/google';
import '@/app/globals.css';
import ReactQueryProvider from '@/components/ReactQueryProvider';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const crimsonText = Crimson_Text({
  subsets: ['latin'],
  weight: ['400', '600'],
  variable: '--font-crimson',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'LexGrid — Indian Legal Research',
  description:
    'AI-powered retrieval-augmented research over Indian Bare Acts.',
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${inter.variable} ${crimsonText.variable}`}>
      <body className="font-sans antialiased bg-parchment text-ink min-h-screen">
        <ReactQueryProvider>{children}</ReactQueryProvider>
      </body>
    </html>
  );
}
