import cv2 as cv
import math
import matplotlib.pyplot as plt
import numpy as np
from pydicom import dcmread
from pydicom.pixel_data_handlers.util import apply_modality_lut

NPS_ROD_DIAMETER_MM = 15
NPS_ROI_DIAMETER_MM = 30
NPS_ROI_DISTCENT_MM = 10 + (NPS_ROD_DIAMETER_MM + NPS_ROI_DIAMETER_MM) / 2  # distance from center


class PixelROI:
    """
    Represent a square or circular ROI. Values represent pixels, this affects rounding.
    """
    def __init__(self, center_x, center_y, size):
        self._center_x = center_x
        self._center_y = center_y
        self._size = size
        print('Building ROI with center in ({},{}) and size {}'.format(center_x, center_y, size))
        self._left = int(self._center_x - self._size / 2 + 0.5)
        self._right = int(self._center_x + self._size / 2 + 0.5)
        self._top = int(self._center_y - self._size / 2 + 0.5)
        self._bottom = int(self._center_y + self._size / 2 + 0.5)
        print('    pixel indexes:', self.yx_indexes())

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

    def yx_indexes(self):
        return [self._top, self._bottom, self._left, self._right]

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
    angle_offset_rad = rad_from_deg(angle_offset_deg)  # angle 0 is at 3 o' clock
    angle_spacing_rad = 2 * math.pi / num_rois
    angles_rad = [angle_offset_rad + r * angle_spacing_rad for r in range(num_rois)]
    return [PixelROI(circle_center_x_px + distance_from_center_px * math.cos(angle),
                     circle_center_y_px + distance_from_center_px * math.sin(angle),
                     roi_size_px) for angle in angles_rad]


def find_phantom_center_and_size(numpy_array):
    ret, thr = cv.threshold(numpy_array.astype(np.uint8), 100, 255, 0)
    contours, hierarchy = cv.findContours(thr, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
    max_r = 0
    [center_x, center_y] = [0, 0]
    for c in contours:
        [x, y], r = cv.minEnclosingCircle(c)
        if r > max_r:
            max_r = r
            [center_x, center_y] = [x, y]
    return [center_x, center_y], max_r


def radial_average(nps_2d_array):
    return [0]


def radial_profile(data, center):
    y, x = np.indices(data.shape)
    r = np.sqrt((x - data.shape[1]/2)**2 + (y - data.shape[0]/2)**2)
    r = r.astype(np.int)
    tbin = np.bincount(r.ravel(), data.ravel())
    nr = np.bincount(r.ravel())
    radialprofile = tbin / nr
    return radialprofile


if __name__ == '__main__':
    #
    # read the images
    #
    images = []
    for i in range(16):
        filename = '/home/cester/git/actilib/src/actilib/resources/dicom/nps/{:04d}_nps.dcm'.format(161-i)
        dicom_data = dcmread(filename)
        images.append(apply_modality_lut(dicom_data.pixel_array, dicom_data))
    pixel_size_xy_mm = np.array(dicom_data.PixelSpacing)
    image_size_xy_px = np.array([len(images[0]), len(images[0][0])])
    image_center_xy_px, section_radius_px = find_phantom_center_and_size(images[0])

    # print('Diameter [mm]:', section_radius_px * 2 * pixel_size_xy_mm)

    # print(image_size_xy_px, image_center_xy_px, pixel_size_xy_mm)

    #
    # create and visualize the ROIs
    #
    roi_diameter_px = NPS_ROI_DIAMETER_MM / pixel_size_xy_mm[0]
    roi_distcent_px = NPS_ROI_DISTCENT_MM / pixel_size_xy_mm[0]
    rois = create_circle_of_rois(8, roi_diameter_px, roi_distcent_px, image_center_xy_px[0], image_center_xy_px[1])

    fig, ax = plt.subplots()
    ax.imshow(images[0], cmap=plt.cm.bone, vmin=-255, vmax=255)
    import matplotlib.patches as patches
    for roi in rois:
        x = roi.edge_l()
        y = roi.edge_t()
        rect = patches.Rectangle((x, y), roi.size(), roi.size(), linewidth=1, edgecolor='r', facecolor='none')
        ax.add_patch(rect)
    plt.show()

    #
    # loop on the ROIs, extract the pixels and calculate the ROI values
    #
    hu_values = []
    nps_series = []
    for i_roi, roi in enumerate(rois):
        [y1, y2, x1, x2] = roi.yx_indexes()
        for image in images:
            roi_pixels = image[y1:y2, x1:x2]  # (!) in "numpy images" the 1st coordinate is y
            # do stuff with the ROI pixels
            hu = np.mean(roi_pixels)
            hu_values.append(hu)
            # nps
            # subtract mean value
            roi_sub = roi_pixels - np.mean(roi_pixels)
            val = np.abs(np.fft.fftshift(np.fft.fftn(roi_sub))) ** 2
            nps_series.append(val)
    print(np.mean(hu_values))
    # applying formula for 2D NPS
    norm = np.prod(pixel_size_xy_mm)/(rois[0].size()**2)
    nps_2d = norm * np.mean(np.array(nps_series), axis=0)
    # radial average of 2D NPS
    nps_1d = radial_average(nps_2d)




