import numpy as np
import os
import pkg_resources
from actilib.helpers.geometry import find_phantom_center_and_radius, find_circles
from actilib.helpers.rois import PixelROI
from actilib.helpers.general import load_images_from_tar
from actilib.helpers.rois import create_circle_of_rois


NPS_ROD_DIAMETER_MM = 15
NPS_ROI_DIAMETER_MM = 30
NPS_ROI_DISTCENT_MM = 10 + (NPS_ROD_DIAMETER_MM + NPS_ROI_DIAMETER_MM) / 2  # distance from center


def main():
    #
    # read the images and basic properties
    #
    tarpath = pkg_resources.resource_filename('actilib', os.path.join('resources', 'dicom_ttf.tar.xz'))
    images, headers = load_images_from_tar(tarpath)
    print('Read', str(len(images)), 'images.')
    pixel_size_xy_mm = np.array(headers[0].PixelSpacing)
    image_size_xy_px = np.array([len(images[0]), len(images[0][0])])
    image_center_xy_px, section_radius_px = find_phantom_center_and_radius(images)

    #
    # find the inserts
    #
    circles = find_circles(images[0], 25/pixel_size_xy_mm[0], 5)
    print(1.5, pixel_size_xy_mm[0], 25/pixel_size_xy_mm[0])
    rois = []

    import cv2
    circles = cv2.HoughCircles(images[0].astype(np.uint8), cv2.HOUGH_GRADIENT, 1, 10,
                               param1=50, param2=20, minRadius=25, maxRadius=35)
    for circle in circles[0]:
        print(circle)
        rois.append(PixelROI(circle[0], circle[1], circle[2], shape='circular'))

    from actilib.helpers.display import display_image_with_rois
    display_image_with_rois(images[0], headers[0], rois)

    #
    # create the ROIs using image pixel coordinates as reference system
    #
    # roi_diameter_px = NPS_ROI_DIAMETER_MM / pixel_size_xy_mm[0]
    # roi_distcent_px = NPS_ROI_DISTCENT_MM / pixel_size_xy_mm[0]
    # rois = create_circle_of_rois(8, roi_diameter_px, roi_distcent_px,
    #                              image_center_xy_px[0], image_center_xy_px[1])

    #
    # loop on the ROIs, extract the pixels and calculate the ROI values
    #


if __name__ == '__main__':
    main()
