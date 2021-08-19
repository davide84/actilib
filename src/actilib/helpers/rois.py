import math
import numpy as np
from actilib.helpers.math import rad_from_deg


class PixelROI:
    """
    Represent a square or circular ROI. Values represent pixels, this affects rounding.
    """
    def __init__(self, center_x, center_y, size, shape='square'):
        self._center_x = center_x
        self._center_y = center_y
        self._size = size
        pixel_offset = 0.5  # 0.5 for basic rounding
        self._left = int(self._center_x - self._size / 2 + pixel_offset)
        self._right = int(self._center_x + self._size / 2 + pixel_offset)
        self._top = int(self._center_y - self._size / 2 + pixel_offset)
        self._bottom = int(self._center_y + self._size / 2 + pixel_offset)
        self._shape = shape
        # print('Built', shape, 'ROI with center in ({},{}) and size {} -> {}'.format(
        #     center_x, center_y, size, self.yx_indexes()))

    def shape(self):
        return self._shape

    def size(self):
        return self._size

    def width(self):
        return self._size

    def height(self):
        return self._size

    def edge_t(self):
        return self._top

    def edge_b(self):
        return self._bottom

    def edge_l(self):
        return self._left

    def edge_r(self):
        return self._right

    def center_x(self):
        return self._center_x

    def center_y(self):
        return self._center_y

    def yx_indexes(self):
        return [self._top, self._bottom, self._left, self._right]

    def get_mask(self, image_size_x, image_size_y=None):
        """"
        Define a pixel mask with 1s corresponding to a square ROI.

        The position of the ROI is defined by "center" attributes and it assumes a common pixel coordinate system with
         0,0 at the top left of the image. The ROI can be totally or partially outside of the image.
        """
        image_size_y = image_size_x if image_size_y is None else image_size_y
        ret_mask = np.zeros((image_size_x, image_size_y))
        if self._shape == 'square':
            if self._left < image_size_x and self._right > 0 and self._top < image_size_y and self._bottom > 0:
                ret_mask[max(0, self.edge_l()):min(image_size_x, self.edge_r()),
                         max(0, self.edge_t()):min(image_size_y, self.edge_b())] = 1
        elif self._shape == 'circular':
            raise NotImplemented('Circular ROIs not yet implemented')
        return ret_mask


def create_circle_of_rois(num_rois, roi_size_px, distance_from_center_px,
                          circle_center_x_px=0, circle_center_y_px=0, angle_offset_deg=0, roi_shape='square'):
    angle_offset_rad = rad_from_deg(angle_offset_deg)  # angle 0 is at 3 o' clock
    angle_spacing_rad = 2 * math.pi / num_rois
    angles_rad = [angle_offset_rad + r * angle_spacing_rad for r in range(num_rois)]
    return [PixelROI(circle_center_x_px + distance_from_center_px * math.cos(angle),
                     circle_center_y_px + distance_from_center_px * math.sin(angle),
                     roi_size_px, roi_shape) for angle in angles_rad]

