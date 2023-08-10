import numpy as np
import os
import pkg_resources
import unittest
from actilib.helpers.dataload import load_images_from_tar
from actilib.helpers.rois import SquareROI, CircleROI
from actilib.helpers.nps import calculate_roi_nps
from actilib.helpers.ttf import ttf_properties
from actilib.helpers.detectability import get_dprime_default_params, calculate_dprime


class TestAnalysis(unittest.TestCase):
    def setUp(self) -> None:
        #
        # read the images and basic properties
        #
        tarpath = pkg_resources.resource_filename('actilib', os.path.join('resources', 'dicom_ttf.tar.xz'))
        self.images = load_images_from_tar(tarpath)
        self.pixel_size_xy_mm = np.array(self.images[0]['header'].PixelSpacing)
        self.image_size_xy_px = np.array([len(self.images[0]['pixels']), len(self.images[0]['pixels'][0])])
        #
        # custom ROIs for comparison with reference
        #
        self.ttf_rois = [CircleROI(16, 304.5, 292.5)]
        self.nps_rois = [SquareROI(64, 311, 156)]

    def test_nps(self):
        nps = calculate_roi_nps(self.images, self.nps_rois, self.pixel_size_xy_mm)
        self.assertAlmostEqual(nps['noise'], 11.2, delta=0.2)
        self.assertAlmostEqual(nps['fpeak'], 0.17, delta=0.02)
        self.assertAlmostEqual(nps['fmean'], 0.21, delta=0.02)

    def test_ttf(self):
        ttf = ttf_properties(self.images, [self.ttf_rois[0]], self.pixel_size_xy_mm, average_images=True)
        self.assertEqual(len(ttf[0]['frq']), 256)
        self.assertAlmostEqual(ttf[0]['frq'][0], 0.0, delta=0.001)
        self.assertAlmostEqual(ttf[0]['frq'][-1], 2.0, delta=0.001)
        self.assertAlmostEqual(ttf[0]['contrast'], 877.5, delta=8.77)  # 1% tolerance
        self.assertAlmostEqual(ttf[0]['f10'], 0.55, delta=0.01)
        self.assertAlmostEqual(ttf[0]['f50'], 0.34, delta=0.01)

    def test_dprime(self):
        nps = calculate_roi_nps(self.images, self.nps_rois, self.pixel_size_xy_mm)
        ttf = ttf_properties(self.images, [self.ttf_rois[0]], self.pixel_size_xy_mm, average_images=True)
        freq = {
            'nps_fx': nps['f2d_x'],
            'nps_fy': nps['f2d_y'],
            'nps_f': nps['f1d'],
            'ttf_f': ttf[0]['frq']
        }
        dprime_params = get_dprime_default_params()
        dprime_params['contrast_hu'] = ttf[0]['contrast']
        dprime = calculate_dprime(freq, nps, ttf[0], params=dprime_params)
        dprime_ref = 150.9
        self.assertAlmostEqual(dprime, dprime_ref, delta=0.01*dprime_ref)  # 1% tolerance


if __name__ == '__main__':
    unittest.main()
