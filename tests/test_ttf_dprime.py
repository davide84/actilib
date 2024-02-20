import numpy as np
import os
import pkg_resources
import traceback
import unittest
from actilib.helpers.io import load_images_from_tar
from actilib.analysis.rois import SquareROI, CircleROI
from actilib.analysis.nps import noise_properties
from actilib.analysis.ttf import ttf_properties
from actilib.analysis.detectability import get_dprime_default_params, calculate_dprime


class TestAnalysis(unittest.TestCase):
    def tearDown(self):
        try:
            etype, value, tb = self._outcome.errors[0][1]
            trace = ''.join(traceback.format_exception(etype=etype, value=value, tb=tb, limit=None))
            print(trace)
        except:
            pass

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
        self.ttf_rois = [CircleROI(16, 305.2, 293.5), CircleROI(16, 246, 202), CircleROI(16, 201, 255)]
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
        self.assertAlmostEqual(ttf['contrast'], 880.0, delta=20)
        self.assertAlmostEqual(ttf['f10'], 0.55, delta=0.01)
        ttf = ttf_list[1]
        self.assertEqual(len(ttf['frq']), 256)
        self.assertAlmostEqual(ttf['frq'][0], 0.0, delta=0.001)
        self.assertAlmostEqual(ttf['frq'][-1], 2.0, delta=0.001)
        self.assertAlmostEqual(ttf['noise'], 11.3, delta=1)
        self.assertAlmostEqual(ttf['contrast'], -962, delta=20)
        self.assertAlmostEqual(ttf['f10'], 0.54, delta=0.02)
        self.assertAlmostEqual(ttf['f50'], 0.33, delta=0.02)
        ttf = ttf_list[2]
        # from actilib.helpers.display import display_image_with_rois
        # display_image_with_rois(self.images[0]['pixels'], self.ttf_rois[2], flag_show=True,
        #                         dicom_header=self.images[0]['header'])
        self.assertEqual(len(ttf['frq']), 256)
        self.assertAlmostEqual(ttf['frq'][0], 0.0, delta=0.001)
        self.assertAlmostEqual(ttf['frq'][-1], 2.0, delta=0.001)
        self.assertAlmostEqual(ttf['noise'], 5.7, delta=1)
        self.assertAlmostEqual(ttf['contrast'], 264.3, delta=20)
        self.assertAlmostEqual(ttf['f10'], 0.57, delta=0.02)
        self.assertAlmostEqual(ttf['f50'], 0.32, delta=0.02)

    def test_dprime(self):
        nps = noise_properties(self.images, self.nps_roi)[0]
        ttf_list = ttf_properties(self.images, self.ttf_rois, average_images=True)
        dprime_references_nofilter = [325, 355, 172]
        dprime_references_npwe = [277, 303, 81]
        for t, ttf in enumerate(ttf_list):
            freq = {
                'nps_fx': nps['f2d_x'],
                'nps_fy': nps['f2d_y'],
                'nps_f': nps['f1d'],
                'ttf_f': ttf['frq']
            }
            tolerance_perc = 2
            # default settings
            dprime_params = get_dprime_default_params()
            dprime_params['contrast_hu'] = ttf['contrast']
            dprime = calculate_dprime(freq, nps, ttf, params=dprime_params)
            self.assertAlmostEqual(dprime, dprime_references_nofilter[t], delta=tolerance_perc*dprime)
            # NPWE filtering
            dprime_params = get_dprime_default_params()
            dprime_params['contrast_hu'] = ttf['contrast']
            dprime_params['view_filter'] = 'NPWE'
            dprime = calculate_dprime(freq, nps, ttf, params=dprime_params)
            self.assertAlmostEqual(dprime, dprime_references_npwe[t], delta=tolerance_perc*dprime)


if __name__ == '__main__':
    unittest.main()
