'use client';

import { useState, useEffect } from 'react';
import ImageGallery from '@/components/ImageGallery';
import logo from "@/img/logo.png"
import Image from 'next/image';

export default function Home() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setRefreshTrigger(prev => prev + 1);
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  return (
    <main className="min-h-screen bg-zinc-900">
      <div className="container mx-auto px-4 py-8">

        <div className="mx-40 mt-20 mb-5 h-30 text-black flex flex-row gap-4 font-[Space Grotesk] justify-center items-center">
          <div className='flex gap-4 px-4'>
            <Image
              className="aspect-square w-28 h-28"
              src={logo}
              alt="KritAI logo"
            ></Image>
            <h1 className='text-white text-[6rem] -translate-y-3 font-semibold ' style={{ fontFamily: 'Space Grotesk' }}>KritAI</h1>
          </div>
        </div>

        <div className="max-w-6xl mx-auto">
          <ImageGallery refreshTrigger={refreshTrigger} />
        </div>
      </div>
    </main>
  );
}
