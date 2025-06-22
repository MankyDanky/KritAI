'use client';

import { useState } from 'react';

interface UploadComponentProps {
  onUploadSuccess: () => void;
}

export default function UploadComponent({ onUploadSuccess }: UploadComponentProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string>('');

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadStatus('');

    try {
      const formData = new FormData();
      formData.append('image', file);

      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();

      if (response.ok) {
        setUploadStatus('Image uploaded successfully!');
        onUploadSuccess();
        // Reset the input
        event.target.value = '';
      } else {
        setUploadStatus(`Error: ${result.error}`);
      }
    } catch (error) {
      setUploadStatus('Upload failed. Please try again.');
      console.error('Upload error:', error);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="mb-8 p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-4 text-gray-800">Upload Image</h2>
      <div className="flex flex-col gap-4">
        <input
          type="file"
          accept="image/*"
          onChange={handleFileUpload}
          disabled={isUploading}
          className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
        />
        {isUploading && (
          <div className="text-blue-600">
            <span className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></span>
            Uploading...
          </div>
        )}
        {uploadStatus && (
          <div className={`text-sm ${uploadStatus.includes('Error') ? 'text-red-600' : 'text-green-600'}`}>
            {uploadStatus}
          </div>
        )}
      </div>
    </div>
  );
}
