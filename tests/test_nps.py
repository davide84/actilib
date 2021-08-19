import numpy as np
import os
import pkg_resources
import unittest
from actilib.helpers.general import load_images_from_tar
from actilib.helpers.geometry import find_phantom_center_and_radius
from actilib.helpers.noise import background_properties
from actilib.helpers.rois import create_circle_of_rois


NPS_ROD_DIAMETER_MM = 15
NPS_ROI_DIAMETER_MM = 30
NPS_ROI_DISTCENT_MM = 10 + (NPS_ROD_DIAMETER_MM + NPS_ROI_DIAMETER_MM) / 2  # distance from center


class TestStringMethods(unittest.TestCase):
    def test_nps(self):
        #
        # read the images and basic properties
        #
        tarpath = pkg_resources.resource_filename('actilib', os.path.join('resources', 'dicom_nps.tar.xz'))
        images, headers = load_images_from_tar(tarpath)
        pixel_size_xy_mm = np.array(headers[0].PixelSpacing)
        image_size_xy_px = np.array([len(images[0]), len(images[0][0])])
        image_center_xy_px, section_radius_px = find_phantom_center_and_radius(images)
        self.assertEqual(len(images), 16)
        self.assertAlmostEqual(pixel_size_xy_mm[0], 0.769, delta=0.001)
        self.assertAlmostEqual(pixel_size_xy_mm[1], 0.769, delta=0.001)
        self.assertEqual(image_size_xy_px[0], 512)
        self.assertEqual(image_size_xy_px[1], 512)
        self.assertAlmostEqual(image_center_xy_px[0], 259.855, delta=0.001)
        self.assertAlmostEqual(image_center_xy_px[1], 257.358, delta=0.001)
        self.assertAlmostEqual(section_radius_px, 177.685, delta=0.001)

        #
        # create the ROIs using image pixel coordinates as reference system
        #
        roi_diameter_px = NPS_ROI_DIAMETER_MM / pixel_size_xy_mm[0]
        roi_distcent_px = NPS_ROI_DISTCENT_MM / pixel_size_xy_mm[0]
        rois = create_circle_of_rois(8, roi_diameter_px, roi_distcent_px,
                                     image_center_xy_px[0], image_center_xy_px[1])

        #
        # loop on the ROIs, extract the pixels and calculate the ROI values
        #
        prop = background_properties(images, rois, pixel_size_xy_mm)
        self.assertAlmostEqual(prop['hu'], -67.306, delta=0.001)
        self.assertAlmostEqual(prop['noise'], 11.866, delta=0.001)
        self.assertAlmostEqual(prop['noise_std'], 0.820, delta=0.001)
        self.assertAlmostEqual(prop['f1d'][2], 0.031, delta=0.001)
        self.assertAlmostEqual(prop['f2d_x'][1], -0.639, delta=0.001)
        self.assertEqual(len(prop['f2d_y']), 128)
        self.assertAlmostEqual(prop['fpeak'], 0.0787, delta=0.001)
        self.assertAlmostEqual(prop['fmean'], 0.209, delta=0.001)
        self.assertAlmostEqual(prop['nps_1d'][3], 350, delta=30)
        self.assertAlmostEqual(prop['nps_2d'][0][0], 0.475, delta=0.001)


if __name__ == '__main__':
    unittest.main()
