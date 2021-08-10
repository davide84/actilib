import cv2 as cv
import numpy as np


def find_phantom_center_and_radius(numpy_array):
    ret, thr = cv.threshold(numpy_array.astype(np.uint8), 100, 255, 0)
    contours, hierarchy = cv.findContours(thr, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
    max_r = 0
    [center_x, center_y] = [0, 0]
    for c in contours:
        [x, y], r = cv.minEnclosingCircle(c)
        if r > max_r:
            max_r = r
            [center_x, center_y] = [x, y]
    return [center_x, center_y], max_r

