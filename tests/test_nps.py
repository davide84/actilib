import numpy as np
import os
import pkg_resources
import unittest
from actilib.helpers.io import load_images_from_tar
from actilib.phantoms.mercury4 import find_phantom_center_and_radius
from actilib.analysis.nps import noise_properties
from actilib.analysis.rois import SquareROI


class TestNPS(unittest.TestCase):
    def load(self, filename):
        tarpath = pkg_resources.resource_filename('actilib', os.path.join('resources', filename))
        self.images = load_images_from_tar(tarpath)
        self.pixel_size_xy_mm = np.array(self.images[0]['header'].PixelSpacing)
        self.image_size_xy_px = np.array([len(self.images[0]['pixels']), len(self.images[0]['pixels'][0])])

    def test_data_load(self):
        self.load('dicom_nps.tar.xz')
        image_center_xy_px, section_radius_px, _, section_radius_mm = find_phantom_center_and_radius(self.images)
        self.assertEqual(len(self.images), 16)
        self.assertAlmostEqual(self.pixel_size_xy_mm[0], 0.769, delta=0.001)
        self.assertAlmostEqual(self.pixel_size_xy_mm[1], 0.769, delta=0.001)
        self.assertEqual(self.image_size_xy_px[0], 512)
        self.assertEqual(self.image_size_xy_px[1], 512)
        self.assertAlmostEqual(image_center_xy_px[0], 258, delta=1)
        self.assertAlmostEqual(image_center_xy_px[1], 256, delta=1)
        self.assertAlmostEqual(2*section_radius_mm, 260, delta=3)

    def test_nps_on_nps_images(self):
        self.load('dicom_nps.tar.xz')
        roi = SquareROI(64, 175, 257)
        nps = noise_properties(self.images, roi, fft_samples=128)
        self.assertAlmostEqual(nps['huavg'], -63.8, delta=4)
        self.assertAlmostEqual(nps['noise'], 10.2, delta=0.2)
        self.assertAlmostEqual(nps['noise_std'], 0.62, delta=0.05)
        self.assertAlmostEqual(nps['fpeak'], 0.16, delta=0.02)
        self.assertAlmostEqual(nps['fmean'], 0.21, delta=0.02)
        self.assertAlmostEqual(max(nps['nps_1d']), 260, delta=15)

    def test_nps_on_ttf_images(self):
        self.load('dicom_ttf.tar.xz')
        roi = SquareROI(64, 309, 156)
        nps = noise_properties(self.images, roi, fft_samples=128)
        self.assertAlmostEqual(nps['huavg'], -64.4, delta=0.1)
        self.assertAlmostEqual(nps['noise'], 10.8, delta=0.3)
        self.assertAlmostEqual(nps['noise_std'], 0.75, delta=0.01)
        self.assertAlmostEqual(nps['fpeak'], 0.17, delta=0.02)
        self.assertAlmostEqual(nps['fmean'], 0.21, delta=0.01)
        self.assertAlmostEqual(max(nps['nps_1d']), 300, delta=10)


if __name__ == '__main__':
    unittest.main()
