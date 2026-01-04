from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode, urljoin, urlparse

if TYPE_CHECKING:
    from .enums import PetPose

__all__: tuple[str, ...] = (
    "outfit_image_url",
    "url_sanitizer",
)


def outfit_image_url(
    *,
    species: int | str,
    color: int | str,
    pose: PetPose,
    style: int | None = None,
    name: str | None = None,
    item_ids: list[int] | None = None,
) -> str:
    """
    Convenience method to get the image url for a DTI outfit.

    The size of the image will be 600x600, not configurable.

    Parameters
    ----------
    species: :class:`int` | :class:`str`
        The species ID of the pet.
    color: :class:`int` | :class:`str`
        The color ID of the pet.
    pose: :class:`PetPose`
        The desired pet pose for the render.
    style: :class:`int` | None
        The alt style ID of the pet.
    name: :class:`str` | None
        The name of the pet.
    item_ids: :class:`list`[ :class:`int`] | None
        A list of item ids to add to the pet.

    Returns
    -------
    :class:`str`
        The image url for the pet appearance.
    """
    parts: dict[str, Any] = {
        "species": species,
        "color": color,
        "pose": pose.name,
    }
    if name:
        # TODO: is this needed?
        parts["name"] = name

    if style:
        parts["style"] = style

    item_ids = item_ids or []
    if item_ids:
        parts["objects[]"] = [str(item_id) for item_id in item_ids]

    return f"https://impress.openneo.net/outfits/new.png?{urlencode(parts, doseq=True)}"


def url_sanitizer(url: str, /) -> str:
    """Convenience method to clean up URLs provided by DTI. Some neo-urls do not include an http/s scheme.

    Parameters
    ----------
    url: :class:`str`
        The string of the url to sanitize.

    """
    if urlparse(url).netloc == "images.neopets.com":
        return urljoin(base="https://images.neopets.com/", url=url)

    return url
