import cv2 as cv
import numpy as np


def find_phantom_center_and_radius(dicom_images):
    if not isinstance(dicom_images, list):
        dicom_images = [dicom_images]
    centers_x = []
    centers_y = []
    radii = []
    for dicom_image in dicom_images:
        numpy_image = dicom_image
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


def find_circles(numpy_image, expected_radius_px, tolerance_px=1):
    """
    Return a list of coordinates for circles matching the desired radius
    """
    circles = []
    ret, thr = cv.threshold(numpy_image.astype(np.uint8), 0, 255, 0)
    img = numpy_image.astype(np.uint8)
    thr = cv.adaptiveThreshold(img, 255, cv.ADAPTIVE_THRESH_GAUSSIAN_C, cv.THRESH_BINARY, 11, 2)
    contours, hierarchy = cv.findContours(thr, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
    for c in contours:
        [x, y], r = cv.minEnclosingCircle(c)
        if r - tolerance_px < expected_radius_px < r + tolerance_px:
            circles.append([x, y, r])
    return circles



