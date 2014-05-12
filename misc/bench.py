import Image
import wand.image
import cv2
import numpy as np
import scipy.misc

def ocv(src, dest, size=(640, 480)):
    img = cv2.imread(src)
    res = cv2.resize(img, size)
    cv2.imwrite(dest, res)

def imgmagick(src, dest, size=(640, 480)):
    img = wand.image.Image(filename=src)
    img.resize(*size)
    img.save(filename=dest)

def pillow(src, dest, size=(640, 480)):
    from PIL import Image
    img = Image.open(src)
    img.thumbnail(size, Image.ANTIALIAS)
    img.save(dest, "JPEG")

def pil(src, dest, size=(640, 480)):
    img = Image.open(src)
    img.thumbnail(size, Image.ANTIALIAS)
    img.save(dest, "JPEG")

"""
%timeit ocv(img, "ocv.jpg")
%timeit imgmagick(img, "im.jpg")
%timeit pil(img, "pil.jpg")
%timeit pillow(img, "pilow.jpg")
"""
