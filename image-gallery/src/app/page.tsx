'use client';

import { useState, useEffect } from 'react';
import ImageGallery from '@/components/ImageGallery';

export default function Home() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setRefreshTrigger(prev => prev + 1);
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  return (
    <main className="min-h-screen bg-gray-100">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold text-center mb-8 text-gray-800">
          Image Gallery
        </h1>
        <div className="max-w-6xl mx-auto">
          <ImageGallery refreshTrigger={refreshTrigger} />
        </div>
      </div>
    </main>
  );
}
