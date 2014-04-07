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


def get_exif_tags(image, mode="silent"):
    """Get a dictionary of exif tags from image exif header

    :param str image: Path to image file.
    :param str mode: Behaviour on missing exif tag. If `"silent"`, `None` is
                     returned. If `"raise"`, a `KeyError` is raised.
    :returns: dict -- The EXIF tag dictionary.
    :raises: KeyError, ValueError

    """
    if mode not in {"silent", "raise"}:
        raise ValueError("Bad get_exif_tag mode '{0}'".format(mode))
    if library == "wand":
        # use the wand library, as either we've been told to or the faster
        # exifread isn't available
        from wand.image import Image
        with Image(filename=image) as img:
            exif = {k[5:]: v for k, v in img.metadata.items() if
                    k.startswith('exif:')}
    elif library == "exifread":
        with open(image, "rb") as fh:
            tags = er.process_file(fh, details=False)
        # remove the first bit off the tags
        exif = {}
        for k, v in tags.items():
            k = unicode(" ".join(k.split(" ")[1:]))
            v = v.values
            if isinstance(v, list):
                v = [unicode(x) for x in v]
                v = ", ".join(v)
            exif[k] = v
    else:
        raise ValueError(
            "Library '{0}' not supported (only wand and exifread are")
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
