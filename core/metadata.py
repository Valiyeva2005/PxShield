"""
PixelShield – Metadata Removal
Strips all EXIF metadata (GPS, camera info, date, author, etc.) from images
before encryption to prevent information leakage.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image


class MetadataRemover:
    """Strips all EXIF and ancillary metadata from PIL Images.

    Usage::

        remover = MetadataRemover()
        clean_image = remover.strip(original_pil_image)
        info = remover.get_metadata_summary(original_pil_image)
    """

    def strip(self, image: Image.Image) -> Image.Image:
        """Return a new :class:`PIL.Image.Image` with all metadata removed.

        The image is re-encoded through a buffer without any ``info`` dict
        entries, EXIF data, ICC profiles, or other ancillary chunks.

        Args:
            image: Source PIL image (any mode).

        Returns:
            A new PIL image without metadata.
        """
        # Re-encode through a PNG buffer (lossless), which drops all EXIF.
        buffer = io.BytesIO()
        # Convert to RGB first to avoid palette/transparency issues.
        img = image.convert("RGB")
        img.save(buffer, format="PNG")
        buffer.seek(0)
        clean = Image.open(buffer)
        clean.load()  # force-load so buffer can be discarded
        return clean.copy()

    def get_metadata_summary(self, image: Image.Image) -> dict:
        """Return a summary of metadata found in *image*.

        Args:
            image: Source PIL image.

        Returns:
            Dict with ``"has_exif"``, ``"exif_keys"``, and ``"format"`` fields.
        """
        exif_data = image.getexif() if hasattr(image, "getexif") else {}
        keys = list(exif_data.keys()) if exif_data else []
        return {
            "has_exif": bool(keys),
            "exif_key_count": len(keys),
            "format": image.format,
            "mode": image.mode,
        }

    def strip_file(self, src: str | Path, dst: str | Path) -> None:
        """Strip metadata from the image at *src* and write to *dst*.

        Args:
            src: Source image file path.
            dst: Destination file path for the stripped image.
        """
        with Image.open(src) as img:
            clean = self.strip(img)
        clean.save(str(dst))


# Module-level singleton.
metadata_remover = MetadataRemover()
