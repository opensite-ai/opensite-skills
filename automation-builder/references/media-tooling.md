# Media Tooling Reference

## ffmpeg

Use for transcoding, thumbnails, clip trimming, and audio extraction.

```bash
# Extract thumbnail at 5 seconds
ffmpeg -i input.mp4 -ss 00:00:05 -frames:v 1 thumbnail.jpg

# Convert to web-optimized H.264
ffmpeg -i input.mov \
  -c:v libx264 -crf 23 -preset fast \
  -c:a aac -b:a 128k \
  -movflags +faststart \
  output.mp4

# Batch convert .mov -> .mp4
for f in *.mov; do
  ffmpeg -i "$f" -c:v libx264 -crf 23 -preset fast "${f%.mov}.mp4"
done

# Extract audio
ffmpeg -i input.mp4 -q:a 0 -map a output.mp3
```

## ImageMagick

Use for bulk format conversion, compositing, overlays, color operations, and PDF rasterization.

```bash
# Resize all JPEGs to max 1200px wide, in-place
mogrify -resize '1200x>' -quality 85 *.jpg

# Convert PNG to WebP
convert input.png -quality 80 output.webp

# Strip EXIF metadata
mogrify -strip *.jpg

# Add watermark in bottom-right corner
convert base.jpg -gravity SouthEast -geometry +10+10 watermark.png -composite output.jpg
```

## Sharp

Use for real-time Node.js image transforms.

```typescript
import sharp from "sharp";

async function generateVariants(input: Buffer, outputDir: string): Promise<void> {
  const sizes = [
    { name: "sm", width: 640 },
    { name: "md", width: 1024 },
    { name: "lg", width: 1536 },
    { name: "full", width: 2560 },
  ];

  await Promise.all(
    sizes.flatMap(({ name, width }) => [
      sharp(input)
        .resize(width, null, { withoutEnlargement: true })
        .webp({ quality: 80 })
        .toFile(`${outputDir}/${name}.webp`),
      sharp(input)
        .resize(width, null, { withoutEnlargement: true })
        .avif({ quality: 60 })
        .toFile(`${outputDir}/${name}.avif`),
    ]),
  );
}
```

Sharp is usually the default for server-side Node.js processing. Use ImageMagick when you need richer CLI workflows or broader format support.
