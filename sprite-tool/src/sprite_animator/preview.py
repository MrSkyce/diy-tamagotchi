from pathlib import Path

from PIL import Image


def write_previews(frames, palette, duration_ms: int, folder: Path):
    width, height = frames[0].size
    sheet = Image.new("RGBA", (width * len(frames), height))
    for index, frame in enumerate(frames):
        frame.save(folder / f"frame_{index:02}.png", optimize=False, compress_level=9)
        sheet.paste(frame, (index * width, 0))
    sheet.save(folder / "sheet.png", optimize=False, compress_level=9)
    sheet.resize((sheet.width * 4, sheet.height * 4), Image.Resampling.NEAREST).save(
        folder / "sheet-4x.png", optimize=False, compress_level=9
    )

    # Fixed palette and exact index mapping: no adaptive quantization or dithering.
    background = (24, 34, 56)
    colors = [background] + sorted(set(palette) - {background})
    lookup = {rgb: i for i, rgb in enumerate(colors)}
    table = [c for rgb in colors for c in rgb]
    table += [0] * (768 - len(table))
    indexed = []
    for frame in frames:
        image = Image.new("P", frame.size)
        image.putpalette(table)
        image.putdata([lookup[p[:3]] if p[3] else 0 for p in frame.get_flattened_data()])
        indexed.append(image)
    # Three cycles are encoded, plus infinite replay. Equal consecutive poses may
    # be coalesced by GIF encoders; their summed duration remains exact.
    sequence = indexed * 3
    for scale in (1, 4):
        images = [
            im.resize((width * scale, height * scale), Image.Resampling.NEAREST) for im in sequence
        ]
        images[0].save(
            folder / f"walk-{scale}x.gif",
            save_all=True,
            append_images=images[1:],
            duration=duration_ms,
            loop=0,
            optimize=False,
            disposal=2,
        )
