import numpy as np
import unittest
from actilib.helpers.rois import SquareROI, CircleROI, get_surrounding_sum, get_surrounding_average

IMG_SIZE = 8
ROI_RADI = IMG_SIZE / 2.0


class TestROIs(unittest.TestCase):
    # test image: a circle of "1" on a background of "0"
    image = np.zeros((IMG_SIZE, IMG_SIZE))
    ind_y, ind_x = np.ogrid[:IMG_SIZE, :IMG_SIZE]
    radii = np.sqrt((ind_x - IMG_SIZE / 2 + 0.5) ** 2 + (ind_y - IMG_SIZE / 2 + 0.5) ** 2)
    mask = radii <= ROI_RADI
    image[mask] = 1

    def test_square_rois(self):
        roi = SquareROI(ROI_RADI, IMG_SIZE/2-0.5, IMG_SIZE/2-0.5)
        self.assertEqual(roi.get_area(), ROI_RADI**2)
        self.assertEqual(roi.get_masked_sum(self.image), 16)
        self.assertEqual(get_surrounding_sum(self.image, roi, ROI_RADI/2), 36)
        self.assertAlmostEqual(get_surrounding_average(self.image, roi, ROI_RADI), 0.75, delta=0.01)
        # ROI smaller than interesting area
        roi.set_size(ROI_RADI/2)
        self.assertEqual(roi.get_area(), 4)
        self.assertEqual(roi.get_masked_sum(self.image), 4)
        self.assertEqual(get_surrounding_sum(self.image, roi, ROI_RADI), 48)
        self.assertAlmostEqual(get_surrounding_average(self.image, roi, ROI_RADI), 0.80, delta=0.01)
        # ROI less smaller than interesing area
        roi.set_size(ROI_RADI*3/2)
        self.assertEqual(roi.get_area(), 36)
        self.assertEqual(roi.get_masked_sum(self.image), 36)
        self.assertEqual(get_surrounding_sum(self.image, roi, ROI_RADI), 16)
        self.assertAlmostEqual(get_surrounding_average(self.image, roi, ROI_RADI), 0.57, delta=0.01)
        # ROI bigger than interesting area
        roi.set_size(ROI_RADI*2)
        self.assertEqual(roi.get_area(), 64)
        self.assertEqual(roi.get_masked_sum(self.image), 52)
        self.assertEqual(get_surrounding_sum(self.image, roi, ROI_RADI), 0)
        self.assertAlmostEqual(get_surrounding_average(self.image, roi, ROI_RADI), 0.00, delta=0.01)

    def test_circular_rois(self):
        roi = CircleROI(ROI_RADI, IMG_SIZE / 2 - 0.5, IMG_SIZE / 2 - 0.5)
        self.assertEqual(roi.get_area(), 52)
        self.assertEqual(roi.get_masked_sum(self.image), 52)
        self.assertEqual(get_surrounding_sum(self.image, roi, ROI_RADI), 0)
        self.assertAlmostEqual(get_surrounding_average(self.image, roi, ROI_RADI), 0.00, delta=0.01)
        # ROI smaller than interesting area
        roi.set_size(ROI_RADI/2)
        self.assertEqual(roi.get_area(), 4)
        self.assertEqual(roi.get_masked_sum(self.image), 4)
        self.assertEqual(get_surrounding_sum(self.image, roi, ROI_RADI), 48)
        self.assertAlmostEqual(get_surrounding_average(self.image, roi, ROI_RADI), 0.80, delta=0.01)
        # ROI bigger than interesting area, and partly bigger than image
        roi.set_size(ROI_RADI*3/2)
        self.assertEqual(roi.get_area(), 32)
        self.assertEqual(roi.get_masked_sum(self.image), 32)
        self.assertEqual(get_surrounding_sum(self.image, roi, ROI_RADI), 20)
        self.assertAlmostEqual(get_surrounding_average(self.image, roi, ROI_RADI), 0.625, delta=0.01)


if __name__ == '__main__':
    unittest.main()
