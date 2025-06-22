import { NextRequest, NextResponse } from 'next/server';
import { getGridFSBucket } from '@/lib/mongodb';
import { Readable } from 'stream';

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get('image') as File;

    if (!file) {
      return NextResponse.json({ error: 'No file uploaded' }, { status: 400 });
    }

    // Validate file type
    if (!file.type.startsWith('image/')) {
      return NextResponse.json({ error: 'Only image files are allowed' }, { status: 400 });
    }

    // Convert File to Buffer
    const arrayBuffer = await file.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    // Get GridFS bucket
    const bucket = await getGridFSBucket();

    // Create a readable stream from the buffer
    const readableStream = new Readable();
    readableStream.push(buffer);
    readableStream.push(null);

    // Upload to GridFS
    const uploadStream = bucket.openUploadStream(file.name, {
      metadata: {
        originalName: file.name,
        contentType: file.type,
        uploadDate: new Date(),
        size: file.size,
      },
    });

    // Pipe the readable stream to GridFS
    const uploadPromise = new Promise((resolve, reject) => {
      uploadStream.on('finish', resolve);
      uploadStream.on('error', reject);
    });

    readableStream.pipe(uploadStream);
    await uploadPromise;

    return NextResponse.json({
      success: true,
      fileId: uploadStream.id,
      filename: file.name,
    });
  } catch (error) {
    console.error('Upload error:', error);
    return NextResponse.json(
      { error: 'Failed to upload image' },
      { status: 500 }
    );
  }
}
