from typing import List, Optional

from .enums import LayerImageSize

__all__ = ("build_layers_url",)


def build_layers_url(layers: List[str], *, size: Optional[LayerImageSize] = None):
    """Convenience method to make the server-side-rendering URL of the provided layer URLs.

    Parameters
    -----------
    layers: List[:class:`str`]
        The image urls, in ascending order of Zone ID's
    size: Optional[:class:`LayerImageSize`]
        The desired size for the render. If one is not supplied, it defaults to `LayerImageSize.SIZE_600`.
    """
    size = str(size or LayerImageSize.SIZE_600)[-3:]  # type: ignore
    joined = ",".join(layers)

    return f"https://impress-2020.openneo.net/api/outfitImage?size={size}&layerUrls={joined}"
