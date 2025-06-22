import { NextRequest, NextResponse } from 'next/server';
import { getGridFSBucket } from '@/lib/mongodb';
import { ObjectId } from 'mongodb';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    if (!id || !ObjectId.isValid(id)) {
      return NextResponse.json({ error: 'Invalid image ID' }, { status: 400 });
    }

    const bucket = await getGridFSBucket();

    // Find the file by ID
    const files = await bucket.find({ _id: new ObjectId(id) }).toArray();

    if (files.length === 0) {
      return NextResponse.json({ error: 'Image not found' }, { status: 404 });
    }

    const file = files[0];

    // Create a download stream
    const downloadStream = bucket.openDownloadStream(new ObjectId(id));

    // Convert stream to buffer
    const chunks: Buffer[] = [];
    for await (const chunk of downloadStream) {
      chunks.push(chunk);
    }
    const buffer = Buffer.concat(chunks);

    // Return the image with proper headers
    return new NextResponse(buffer, {
      headers: {
        'Content-Type': file.metadata?.contentType || 'image/jpeg',
        'Content-Length': file.length.toString(),
        'Cache-Control': 'public, max-age=31536000',
      },
    });
  } catch (error) {
    console.error('Error serving image:', error);
    return NextResponse.json(
      { error: 'Failed to serve image' },
      { status: 500 }
    );
  }
}
