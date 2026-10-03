import io
import warnings

from PIL import Image, ImageOps


def prepare_image(image_bytes):
    if len(image_bytes) > 10 * 1024 * 1024:
        raise ValueError("Choose an image smaller than 10 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(image_bytes)) as original:
                if original.format not in ("JPEG", "PNG"):
                    raise ValueError("Choose a JPG or PNG image.")
                if original.width * original.height > 20_000_000:
                    raise ValueError("Choose an image with fewer than 20 million pixels.")
                image = ImageOps.exif_transpose(original).convert("RGB")
                image.thumbnail((2048, 2048))
        return image
    except (OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValueError("This image could not be opened. Choose a valid JPG or PNG.") from None


def image_for_chat(image):
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()
