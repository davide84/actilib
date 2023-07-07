import copy
import math
import numpy as np
import numpy.ma as ma
from actilib.helpers.math import rad_from_deg


class PixelROI:
    """
    Represent a generic ROI. Values represent pixels, this affects rounding.
    """
    def __init__(self, size, center_x, center_y):
        self._size = size
        self._center_x = center_x
        self._center_y = center_y

    def shape(self):
        raise NotImplemented

    def size(self):
        return self._size

    def set_size(self, size):
        self._size = size

    def width(self, margin=0.0):
        return int(self._size + 2 * margin + 0.5)

    def height(self, margin=0.0):
        return int(self._size + 2 * margin + 0.5)

    def edge_t(self, margin=0.0):
        return int(self._center_y - self._size / 2 - margin + 0.5)  # 0.5 for basic rounding

    def edge_b(self, margin=0.0):
        return int(self._center_y + self._size / 2 + margin + 0.5)  # 0.5 for basic rounding

    def edge_l(self, margin=0.0):
        return int(self._center_x - self._size / 2 - margin + 0.5)  # 0.5 for basic rounding

    def edge_r(self, margin=0.0):
        return int(self._center_x + self._size / 2 + margin + 0.5)  # 0.5 for basic rounding

    def indexes_yx(self):
        return [self.edge_t(), self.edge_b(), self.edge_l(), self.edge_r()]

    def center_x(self):
        return self._center_x

    def center_y(self):
        return self._center_y

    def set_center(self, center_x, center_y):
        self._center_x = center_x
        self._center_y = center_y

    def get_mask(self, image=None):
        return self.get_annular_mask(image, margin_inner=-self.size() / 2.0)

    def get_annular_mask(self, image=None, margin_outer=0.0, margin_inner=0.0):
        raise NotImplemented

    def get_area(self):
        return np.sum(self.get_mask())

    def get_masked_sum(self, image):
        return np.sum(np.multiply(image, self.get_mask(image)))

    def get_distance_from_center(self, image=None, array_size_yx=None):
        if image is not None:
            grid_y, grid_x = np.ogrid[:image.shape[1], :image.shape[0]]
        elif array_size_yx is not None:
            grid_y, grid_x = np.ogrid[:array_size_yx[0], :array_size_yx[1]]
        else:
            grid_y, grid_x = np.ogrid[:self.height(), :self.width()]
        roi_center_x = self.size() / 2 - 0.5 if image is None else self.center_x()
        roi_center_y = self.size() / 2 - 0.5 if image is None else self.center_y()
        return np.sqrt((grid_x - roi_center_x) ** 2 + (grid_y - roi_center_y) ** 2)

    def get_masked_distance_from_center(self, image=None):
        return np.multiply(self.get_mask(image), self.get_distance_from_center(image))


class SquareROI(PixelROI):
    def __init__(self, side, center_x=None, center_y=None):
        super().__init__(side,
                         center_x if center_x is not None else side / 2.0,
                         center_y if center_y is not None else side / 2.0)

    def side(self):
        return int(self._size + 0.5)

    def shape(self):
        return 'square'

    def get_annular_mask(self, image=None, margin_outer=0.0, margin_inner=0.0):
        """"
        Define an annular pixel mask which has the same center as the ROI. For default values it returns the ROI mask.

        The position of the ROI is defined by "center" attributes and it assumes a common pixel coordinate system with
         0,0 at the top left of the image. The ROI can be totally or partially outside of the image.
        """
        if image is None:
            return np.ones((self.height(), self.width()))
        mask = np.zeros(image.shape)
        if margin_inner < margin_outer:
            mask[max(0, self.edge_t(margin_outer)):min(mask.shape[0], self.edge_b(margin_outer)),
                 max(0, self.edge_l(margin_outer)):min(mask.shape[1], self.edge_r(margin_outer))] = 1
            mask[max(0, self.edge_t(margin_inner)):min(mask.shape[0], self.edge_b(margin_inner)),
                 max(0, self.edge_l(margin_inner)):min(mask.shape[1], self.edge_r(margin_inner))] = 0
        return mask.astype(int)


class CircleROI(PixelROI):
    def __init__(self, radius, center_x=None, center_y=None):
        super().__init__(2 * radius,
                         center_x if center_x is not None else radius,
                         center_y if center_y is not None else radius)

    def radius(self):
        return int(self._size / 2.0 + 0.5)

    def shape(self):
        return 'circle'

    def get_annular_mask(self, image=None, margin_outer=0.0, margin_inner=0.0):
        """"
        Define an annular pixel mask which has the same center as the ROI. For default values it returns the ROI mask.

        The position of the ROI is defined by "center" attributes and it assumes a common pixel coordinate system with
         0,0 at the top left of the image. The ROI can be totally or partially outside of the image.
        """
        mask_size_x = int(self.width() + margin_outer + 0.5) if image is None else image.shape[1]
        mask_size_y = int(self.height() + margin_outer + 0.5) if image is None else image.shape[0]
        mask = np.zeros((mask_size_x, mask_size_y))
        if margin_inner < margin_outer:
            dist_from_center = self.get_distance_from_center(image, (mask_size_y, mask_size_x))
            mask[dist_from_center <= self.radius() + margin_outer] = 1
            mask[dist_from_center <= self.radius() + margin_inner] = 0
        return mask.astype(int)


def create_circle_of_rois(num_rois, roi_size_px, distance_from_center_px,
                          circle_center_x_px=0, circle_center_y_px=0, angle_offset_deg=0, roi_shape='square'):
    angle_offset_rad = rad_from_deg(angle_offset_deg)  # angle 0 is at 3 o' clock
    angle_spacing_rad = 2 * math.pi / num_rois
    angles_rad = [angle_offset_rad + r * angle_spacing_rad for r in range(num_rois)]
    if roi_shape == 'square':
        return [SquareROI(roi_size_px,
                          circle_center_x_px + distance_from_center_px * math.cos(angle),
                          circle_center_y_px + distance_from_center_px * math.sin(angle)) for angle in angles_rad]
    elif roi_shape == 'circle':
        return [CircleROI(roi_size_px / 2.0,
                          circle_center_x_px + distance_from_center_px * math.cos(angle),
                          circle_center_y_px + distance_from_center_px * math.sin(angle)) for angle in angles_rad]


def get_masked_image(pixels, mask):
    return ma.masked_array(pixels, mask=1-mask)


def get_surrounding_sum(image, roi_small, margin=None):
    margin = roi_small.size() / 2.0 if margin is None else margin
    # build a second ROI
    roi_large = copy.deepcopy(roi_small)
    roi_large.set_size(roi_small.size() + 2 * margin)
    sum_small = roi_small.get_masked_sum(image)
    sum_large = roi_large.get_masked_sum(image)
    return sum_large - sum_small


def get_surrounding_average(image, roi, margin_outer, margin_inner=0):
    # build a second ROI
    roi_small = roi
    if margin_inner > 0:
        roi_small = copy.deepcopy(roi)
        roi_small.set_size(roi.size() + 2 * margin_inner)
    roi_large = copy.deepcopy(roi)
    roi_large.set_size(roi.size() + 2 * margin_outer)
    area_small = np.sum(roi_small.get_mask(image))
    area_large = np.sum(roi_large.get_mask(image))
    if area_large == area_small:  # both ROIs bigger or equal to image
        return 0.0
    sum_small = roi_small.get_masked_sum(image)
    sum_large = roi_large.get_masked_sum(image)
    return (sum_large - sum_small) / (area_large - area_small)
