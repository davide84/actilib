import numpy as np
import os
import pkg_resources
import tarfile
from pydicom import dcmread
from pydicom.pixel_data_handlers.util import apply_modality_lut
from actilib.helpers.geometry import find_phantom_center_and_radius
from actilib.helpers.rois import create_circle_of_rois


NPS_ROD_DIAMETER_MM = 15
NPS_ROI_DIAMETER_MM = 30
NPS_ROI_DISTCENT_MM = 10 + (NPS_ROD_DIAMETER_MM + NPS_ROI_DIAMETER_MM) / 2  # distance from center


def main():
    #
    # read the images and basic properties
    #
    images = []
    tarpath = pkg_resources.resource_filename('actilib', os.path.join('resources', 'dicom_ttf.tar.xz'))
    with tarfile.open(tarpath, encoding='utf-8') as file_tar:
        for file_name in file_tar.getmembers():
            file_dcm = file_tar.extractfile(file_name)
            dicom_data = dcmread(file_dcm)
            images.append(apply_modality_lut(dicom_data.pixel_array, dicom_data))
    pixel_size_xy_mm = np.array(dicom_data.PixelSpacing)
    image_size_xy_px = np.array([len(images[0]), len(images[0][0])])
    image_center_xy_px, section_radius_px = find_phantom_center_and_radius(images[0])

    #
    # create and visualize the ROIs
    #
    roi_diameter_px = NPS_ROI_DIAMETER_MM / pixel_size_xy_mm[0]
    roi_distcent_px = NPS_ROI_DISTCENT_MM / pixel_size_xy_mm[0]
    rois = create_circle_of_rois(8, roi_diameter_px, roi_distcent_px,
                                 image_center_xy_px[0], image_center_xy_px[1])

    #
    # loop on the ROIs, extract the pixels and calculate the ROI values
    #


if __name__ == '__main__':
    main()
