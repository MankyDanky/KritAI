import { NextResponse } from 'next/server';
import { getGridFSBucket } from '@/lib/mongodb';

export async function GET() {
  try {
    const bucket = await getGridFSBucket();

    // Find all files in GridFS
    const files = await bucket.find({}).toArray();

    // Format the response
    const imageList = files.map((file) => ({
      id: file._id.toString(),
      filename: file.filename,
      originalName: file.metadata?.originalName || file.filename,
      contentType: file.metadata?.contentType || 'image/jpeg',
      uploadDate: file.uploadDate,
      size: file.length,
    }));

    return NextResponse.json({ images: imageList });
  } catch (error) {
    console.error('Error fetching images:', error);
    return NextResponse.json(
      { error: 'Failed to fetch images' },
      { status: 500 }
    );
  }
}
