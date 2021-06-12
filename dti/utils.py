from typing import List, Optional
from urllib.parse import urljoin, urlparse

from .enums import LayerImageSize

__all__ = ("build_layers_url", "url_sanitizer")


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


def url_sanitizer(url: str) -> str:
    """Convenience method to clean up URLs provided by DTI. Some neo-urls do not include an http/s scheme.

    Parameters
    -----------
    url: :class:`str`
        The string of the url to sanitize.
    """

    if "images.neopets.com" == urlparse(url).netloc:
        return urljoin(base="http://images.neopets.com/", url=url)

    return url