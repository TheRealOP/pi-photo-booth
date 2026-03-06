from PIL import Image, ImageOps


def make_collage(
    image_paths,
    output_path,
    grid=(2, 2),
    tile_size=(600, 600),
    padding=20,
    bg_color=(255, 255, 255),
):
    cols, rows = grid
    if len(image_paths) != cols * rows:
        raise ValueError("image_paths count must match grid size")

    tile_width, tile_height = tile_size
    canvas_width = cols * tile_width + (cols + 1) * padding
    canvas_height = rows * tile_height + (rows + 1) * padding

    canvas = Image.new("RGB", (canvas_width, canvas_height), bg_color)

    for index, path in enumerate(image_paths):
        image = Image.open(path)
        tile = ImageOps.fit(image, tile_size, Image.LANCZOS)

        col = index % cols
        row = index // cols
        x = padding + col * (tile_width + padding)
        y = padding + row * (tile_height + padding)
        canvas.paste(tile, (x, y))

    canvas.save(output_path, "JPEG", quality=95)
    return output_path
