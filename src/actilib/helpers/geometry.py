import cv2 as cv
import numpy as np


def find_phantom_center_and_radius(numpy_images):
    if not isinstance(numpy_images, list):
        numpy_images = [numpy_images]
    centers_x = []
    centers_y = []
    radii = []
    for numpy_image in numpy_images:
        ret, thr = cv.threshold(numpy_image.astype(np.uint8), 100, 255, 0)
        contours, hierarchy = cv.findContours(thr, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
        max_r = 0
        [center_x, center_y] = [0, 0]
        for c in contours:
            [x, y], r = cv.minEnclosingCircle(c)
            if r > max_r:
                max_r = r
                [center_x, center_y] = [x, y]
        centers_x.append(center_x)
        centers_y.append(center_y)
        radii.append(max_r)
    return [np.mean(centers_x), np.mean(centers_y)], np.mean(radii)

