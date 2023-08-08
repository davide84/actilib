import numpy as np
import os
import pkg_resources
from actilib.helpers.geometry import find_phantom_center_and_radius, find_circles
from actilib.helpers.general import load_images_from_tar
from actilib.helpers.rois import SquareROI, CircleROI, create_circle_of_rois
from actilib.helpers.noise import background_properties
from actilib.helpers.ttf import ttf_properties
from actilib.helpers.detectability import calculate_dprime


NPS_ROD_DIAMETER_MM = 15
NPS_ROI_DIAMETER_MM = 30
NPS_ROI_DISTCENT_MM = 10 + (NPS_ROD_DIAMETER_MM + NPS_ROI_DIAMETER_MM) / 2  # distance from center


def main():
    #
    # read the images and basic properties
    #
    tarpath = pkg_resources.resource_filename('actilib', os.path.join('resources', 'dicom_ttf.tar.xz'))
    images = load_images_from_tar(tarpath)
    print('Read', str(len(images)), 'images.')
    pixel_size_xy_mm = np.array(images[0]['header'].PixelSpacing)
    image_size_xy_px = np.array([len(images[0]['pixels']), len(images[0]['pixels'][0])])
    image_center_xy_px, section_radius_px, _, _ = find_phantom_center_and_radius(images)

    #
    # custom ROIs for comparison with reference
    #
    ttf_rois = [CircleROI(16, 304.5, 292.5)]
    nps_rois = [SquareROI(64, 311, 156)]

    from actilib.helpers.display import display_image_with_rois
    # display_image_with_rois(images[0]['window'], ttf_rois)

    # quick NPS test
    nps = background_properties(images, nps_rois, pixel_size_xy_mm)
    # print(nps)
    # print('noise =', nps['noise'])
    # print('fpeak =', nps['fpeak'])
    # print('nps1d =', nps['nps_1d'])

    # TTF test
    ttf = ttf_properties(images, [ttf_rois[0]], pixel_size_xy_mm, average_images=True)
    # print(ttf[0]['frq'])

    freq = {
        'nps_fx': nps['f2d_x'],
        'nps_fy': nps['f2d_y'],
        'nps_f': nps['f1d'],
        'ttf_f': ttf[0]['frq']
    }

    #
    # d' test
    #
    dprime = calculate_dprime(freq, nps, ttf[0])
    for key in nps:
        print(key, nps[key])
    print('DPRIME:', dprime)


if __name__ == '__main__':
    main()
