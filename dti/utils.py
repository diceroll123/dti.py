from __future__ import annotations

from urllib.parse import quote, urljoin, urlparse

from .enums import LayerImageSize

__all__: tuple[str, ...] = (
    "build_layers_url",
    "url_sanitizer",
)


def build_layers_url(
    layers: list[str],
    /,
    size: LayerImageSize | None = None,
) -> str:
    """Convenience method to make the server-side-rendering URL of the provided layer URLs.

    Parameters
    -----------
    layers: List[:class:`str`]
        The image urls, in ascending order of Zone ID's
    size: Optional[:class:`LayerImageSize`]
        The desired size for the render. If one is not supplied, it defaults to `LayerImageSize.SIZE_600`.
    """
    size_str = str(size or LayerImageSize.SIZE_600)[-3:]
    joined = ",".join(quote(layer) for layer in layers)

    return f"https://impress-2020.openneo.net/api/outfitImage?size={size_str}&layerUrls={joined}"


def url_sanitizer(url: str, /) -> str:
    """Convenience method to clean up URLs provided by DTI. Some neo-urls do not include an http/s scheme.

    Parameters
    -----------
    url: :class:`str`
        The string of the url to sanitize.
    """

    if urlparse(url).netloc == "images.neopets.com":
        return urljoin(base="https://images.neopets.com/", url=url)

    return url
