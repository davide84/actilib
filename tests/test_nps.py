import math

import numpy as np


class PixelROI:
    """
    Represent a square or circular ROI. Values represent pixels, this affects rounding.
    """
    def __init__(self, center_x, center_y, size):
        self._center_x = center_x
        self._center_y = center_y
        self._size = size
        print('Building ROI with center in ({},{}) and size {}'.format(center_x, center_y, size))
        self._top = int(self._center_x - self._size / 2 + 0.5)
        self._bottom = int(self._center_x + self._size / 2 + 0.5)
        self._left = int(self._center_y - self._size / 2 + 0.5)
        self._right = int(self._center_y + self._size / 2 + 0.5)

    def edge_t(self):
        return self._top

    def edge_b(self):
        return self._bottom

    def edge_l(self):
        return self._left

    def edge_r(self):
        return self._right

    def square_mask(self, image_size_x, image_size_y=None):
        """"
        Define a pixel mask with 1s corresponding to a square ROI.

        The position of the ROI is defined by "center" attributes and it assumes a common pixel coordinate system with
         0,0 at the top left of the image. The ROI can be totally or partially outside of the image.
        """
        image_size_y = image_size_x if image_size_y is None else image_size_y
        ret_mask = np.zeros((image_size_x, image_size_y))
        if self._left < image_size_x and self._right > 0 and self._top < image_size_y and self._bottom > 0:
            ret_mask[max(0, self.edge_l()):min(image_size_x, self.edge_r()),
                     max(0, self.edge_t()):min(image_size_y, self.edge_b())] = 1
        return ret_mask


def rad_from_deg(deg):
    return deg * 2 * math.pi / 360.0


def create_circle_of_rois(num_rois, roi_size_px, distance_from_center_px,
                          circle_center_x_px=0, circle_center_y_px=0, angle_offset_deg=0):
    angle_offset_rad = rad_from_deg(angle_offset_deg - 90)  # so that it starts from 12 o' clock
    angle_spacing_rad = 2 * math.pi / num_rois
    angles_rad = [angle_offset_rad + i * angle_spacing_rad for i in range(num_rois)]
    return [PixelROI(circle_center_x_px + distance_from_center_px * math.cos(angle),
                     circle_center_y_px + distance_from_center_px * math.sin(angle),
                     roi_size_px) for angle in angles_rad]


if __name__ == '__main__':
    rois = create_circle_of_rois(8, 4, 8, 10, 10)
    mask = np.zeros((20, 20))
    for roi in rois:
        mask += roi.square_mask(20)
    print(mask)

