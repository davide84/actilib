import numpy as np
import os
import pkg_resources
from actilib.helpers.mercury import find_phantom_center_and_radius, find_circles
from actilib.helpers.rois import PixelROI
from actilib.helpers.dataload import load_images_from_tar
from actilib.helpers.rois import create_circle_of_rois


NPS_ROD_DIAMETER_MM = 15
NPS_ROI_DIAMETER_MM = 30
NPS_ROI_DISTCENT_MM = 10 + (NPS_ROD_DIAMETER_MM + NPS_ROI_DIAMETER_MM) / 2  # distance from center


def main():
    #
    # read the images and basic properties
    #
    tarpath = pkg_resources.resource_filename('actilib', os.path.join('resources', 'dicom_not.tar.xz'))
    images = load_images_from_tar(tarpath)
    print('Read', str(len(images)), 'images.')
    pixel_size_xy_mm = np.array(images[0]['header'].PixelSpacing)
    image_size_xy_px = np.array([len(images[0]['pixels']), len(images[0]['pixels'][0])])

    from actilib.phantoms.mercury4 import classify_slices
    flags = classify_slices(images)
    print(flags)


if __name__ == '__main__':
    main()
