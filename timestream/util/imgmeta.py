"""
.. module:: imgmeta
    :platform: Unix, Windows
    :synopsis: Access image metadata such as EXIF tags.

.. moduleauthor:: Kevin Murray <spam@kdmurray.id.au>
"""
try:
    import exifread as er
    library = "exifread"
except ImportError:
    library = "wand"
from string import (
        digits,
        )

from timestream.util import (
        dict_unicode_to_str,
        )

def get_exif_tags(image, mode="silent"):
    """Get a dictionary of exif tags from image exif header

    :param str image: Path to image file.
    :param str mode: Behaviour on missing exif tag. If `"silent"`, `None` is
                     returned. If `"raise"`, a `KeyError` is raised.
    :returns: dict -- The EXIF tag dictionary, or None
    :raises: ValueError
    """
    if mode not in {"silent", "raise"}:
        raise ValueError("Bad get_exif_tags mode '{}'".format(mode))
    if library == "wand":
        # use the wand library, as either we've been told to or the faster
        # exifread isn't available
        from wand.image import Image
        with Image(filename=image) as img:
            exif = {k[5:]: v for k, v in img.metadata.items() if
                    k.startswith('exif:')}
    elif library == "exifread":
        import exifread as er
        with open(image, "rb") as fh:
            tags = er.process_file(fh, details=False)
        tags = dict_unicode_to_str(tags)
        # remove the first bit off the tags
        exif = {}
        for k, v in tags.items():
            # Remove the EXIF/Image category from the keys
            k = " ".join(k.split(" ")[1:])
            # weird exif tags in CR2s start with a 2/3, or have hex in them
            if k[0] in digits or "0x" in k:
                continue
            v = str(v)
            exif[k] = v
    else:
        raise ValueError(
            "Library '{}' not supported (only wand and exifread are".format(
                library))
    return exif

def get_exif_tag(image, tag, mode="silent"):
    """Get a tag from image exif header

    :param str image: Path to image file.
    :param str tag: Tag to extract from exif header.
    :param str mode: Behaviour on missing exif tag. If `"silent"`, `None` is
                     returned. If `"raise"`, a `KeyError` is raised.
    :returns: str -- The EXIF tag value.
    :raises: KeyError, ValueError
    """
    if mode not in {"silent", "raise"}:
        raise ValueError("Bad get_exif_tag mode '{0}'".format(mode))
    exif = get_exif_tags(image, mode)
    try:
        return exif[tag]
    except KeyError as exc:
        if mode == "silent":
            return None
        else:
            raise exc
