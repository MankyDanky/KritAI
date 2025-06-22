import type { Metadata } from "next";
import { Geist, Geist_Mono, Overpass, Reenie_Beanie, Space_Grotesk, Space_Mono  } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

import { } from 'next/font/google';

const overpass = Overpass({ subsets: ['latin'], variable: '--font-overpass' });
const beanie = Reenie_Beanie({ subsets: ['latin'], variable: '--font-beanie', weight: '400' });
const grotesk = Space_Grotesk({ subsets: ['latin'], variable: '--font-grotesk' });
const mono = Space_Mono({ subsets: ['latin'], weight: ['400', '700'], variable: '--font-mono' });

export const metadata: Metadata = {
  title: "KritAI",
  description: "Empowering artists with a powerful AI toolkit",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${overpass.variable} ${beanie.variable} ${grotesk.variable} ${mono.variable}`}>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
