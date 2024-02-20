import numpy as np
import os
import pkg_resources
import unittest
from actilib.helpers.io import load_images_from_tar
from actilib.analysis.rois import SquareROI, CircleROI
from actilib.analysis.nps import noise_properties
from actilib.analysis.ttf import ttf_properties
from actilib.analysis.detectability import get_dprime_default_params, calculate_dprime


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
        self.ttf_rois = [CircleROI(16, 305.2, 293.5), CircleROI(16, 246, 202)]
        self.nps_roi = SquareROI(64, 309, 156)

    def test_nps(self):
        nps = noise_properties(self.images, self.nps_roi)[0]
        self.assertAlmostEqual(nps['noise'], 10.8, delta=0.3)
        self.assertAlmostEqual(nps['fpeak'], 0.17, delta=0.02)

    def test_ttf(self):
        ttf_list = ttf_properties(self.images, self.ttf_rois, average_images=True)
        ttf = ttf_list[0]
        self.assertEqual(len(ttf['frq']), 256)
        self.assertAlmostEqual(ttf['frq'][0], 0.0, delta=0.001)
        self.assertAlmostEqual(ttf['frq'][-1], 2.0, delta=0.001)
        self.assertAlmostEqual(ttf['noise'], 12, delta=1)
        self.assertAlmostEqual(ttf['contrast'], 880.0, delta=17.6)  # 2% tolerance
        self.assertAlmostEqual(ttf['f10'], 0.55, delta=0.01)
        ttf = ttf_list[1]
        self.assertEqual(len(ttf['frq']), 256)
        self.assertAlmostEqual(ttf['frq'][0], 0.0, delta=0.001)
        self.assertAlmostEqual(ttf['frq'][-1], 2.0, delta=0.001)
        self.assertAlmostEqual(ttf['noise'], 12.0, delta=0.1)
        self.assertAlmostEqual(ttf['contrast'], -970, delta=19.4)  # 2% tolerance
        self.assertAlmostEqual(ttf['f10'], 0.54, delta=0.02)
        self.assertAlmostEqual(ttf['f50'], 0.33, delta=0.02)

    def test_dprime(self):
        nps = noise_properties(self.images, self.nps_roi)[0]
        ttf_list = ttf_properties(self.images, self.ttf_rois, average_images=True)
        dprime_references = [155.4, 171.8]
        for t, ttf in enumerate(ttf_list):
            freq = {
                'nps_fx': nps['f2d_x'],
                'nps_fy': nps['f2d_y'],
                'nps_f': nps['f1d'],
                'ttf_f': ttf['frq']
            }
            dprime_params = get_dprime_default_params()
            dprime_params['contrast_hu'] = ttf['contrast']
            dprime = calculate_dprime(freq, nps, ttf, params=dprime_params)
            self.assertAlmostEqual(dprime, dprime_references[t], delta=0.01*dprime)  # 1% tolerance


if __name__ == '__main__':
    unittest.main()
