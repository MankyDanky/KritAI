'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';

interface ImageData {
  id: string;
  filename: string;
  originalName: string;
  contentType: string;
  uploadDate: string;
  size: number;
}

interface ImageGalleryProps {
  refreshTrigger: number;
}

export default function ImageGallery({ refreshTrigger }: ImageGalleryProps) {
  const [images, setImages] = useState<ImageData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  const fetchImages = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/images');
      const data = await response.json();

      if (response.ok) {
        setImages(data.images);
        setError('');
      } else {
        setError(data.error || 'Failed to fetch images');
      }
    } catch (err) {
      setError('Failed to fetch images');
      console.error('Fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchImages();
  }, [refreshTrigger]);

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading images...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">{error}</p>
        <button
          onClick={fetchImages}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (images.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600 text-lg">No images uploaded yet.</p>
        <p className="text-gray-500 mt-2">Upload your first image above!</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">
        Image Gallery ({images.length} images)
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {images.map((image) => (
          <div key={image.id} className="bg-gray-50 rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow">
            <div className="relative aspect-square">
              <Image
                src={`/api/images/${image.id}`}
                alt={image.originalName}
                fill
                className="object-cover"
                sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
              />
            </div>
            <div className="p-3">
              <p className="text-sm font-medium text-gray-800 truncate">
                {image.originalName}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {new Date(image.uploadDate).toLocaleDateString()}
              </p>
              <p className="text-xs text-gray-500">
                {(image.size / 1024).toFixed(1)} KB
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
