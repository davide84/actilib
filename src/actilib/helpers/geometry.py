import cv2 as cv
import numpy as np


def find_phantom_center_and_radius(dicom_images):
    if not isinstance(dicom_images, list):
        dicom_images = [dicom_images]
    centers_x = []
    centers_y = []
    radii = []
    for dicom_image in dicom_images:
        ret, thr = cv.threshold(dicom_image['window'].astype(np.uint8), 100, 255, 0)
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
    pixel_size_xy_mm = np.array(dicom_images[0]['header'].PixelSpacing)
    radius_factor_mm = ((pixel_size_xy_mm[0]**2 + pixel_size_xy_mm[1]**2) / 2)**0.5
    ret_xy = [np.mean(centers_x), np.mean(centers_y)]
    ret_r = np.mean(radii)
    return ret_xy, ret_r, np.multiply(ret_xy, pixel_size_xy_mm), ret_r * radius_factor_mm


def find_circles(numpy_image, expected_radius_px, tolerance_px=1):
    """
    Return a list of coordinates for circles matching the desired radius
    """
    circles = []
    img = numpy_image.astype(np.uint8)
    ret, thrimg = cv.threshold(img, 127, 255, 0)
    # from actilib.helpers.display import display_pixels
    # display_pixels(thrimg)
    thr = cv.adaptiveThreshold(img, 255, cv.ADAPTIVE_THRESH_GAUSSIAN_C, cv.THRESH_BINARY, 11, 2)
    contours, hierarchy = cv.findContours(thr, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
    for c in contours:
        [x, y], r = cv.minEnclosingCircle(c)
        if r - tolerance_px < expected_radius_px < r + tolerance_px:
            circles.append([x, y, r])
    return circles


def find_weighted_center(image):
    mesh_x, mesh_y = np.meshgrid(range(len(image[0])), range(len(image)))
    total = np.sum(image)
    cx = np.sum(np.multiply(mesh_x, image)) / total
    cy = np.sum(np.multiply(mesh_y, image)) / total
    return cx, cy
