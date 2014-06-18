import skimage.io as skimgio
import cv2
import time
ROUNDS = 1

def load_scikit(img):
    a = skimgio.imread(img, plugin="freeimage")
    skimgio.imsave("./scikit.tiff", a, plugin="freeimage")
    print a.shape, a.dtype

def load_cv(img):
    a = cv2.imread(img, -2)
    cv2.imwrite("./cv2.tiff", a)
    print a.shape, a.dtype

def main(img):
    start = time.time()
    for _ in range(ROUNDS):
        load_scikit(img)
    print "Scikit image took {:.4f} seconds".format(time.time() - start)
    start = time.time()
    for _ in range(ROUNDS):
        load_cv(img)
    print "OpenCV took {:.4f} seconds".format(time.time() - start)

if __name__ == "__main__":
    import sys
    main(sys.argv[1])
