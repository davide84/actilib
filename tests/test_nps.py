import cv2 as cv
import math
import matplotlib.pyplot as plt
import numpy as np
from pydicom import dcmread
from pydicom.pixel_data_handlers.util import apply_modality_lut
from actilib.helpers.geometry import find_phantom_center_and_radius
from actilib.helpers.math import cart2pol, subtract_2d_poly_mean
from actilib.helpers.rois import PixelROI, create_circle_of_rois


NPS_ROD_DIAMETER_MM = 15
NPS_ROI_DIAMETER_MM = 30
NPS_ROI_DISTCENT_MM = 10 + (NPS_ROD_DIAMETER_MM + NPS_ROI_DIAMETER_MM) / 2  # distance from center


def fft_frequencies(n_samples, pixel_size_mm):
    sampling_rate = 1 / pixel_size_mm
    frequency_spacing = sampling_rate / n_samples
    frequencies = [frequency_spacing * ns for ns in range(n_samples)]
    frequencies_shifted = np.fft.fftshift(frequencies)
    dc_index = np.where(frequencies_shifted == 0)[0][0]
    frequencies = [f - frequencies[dc_index] for f in frequencies]
    return frequencies


def radial_profile(r_matrix, data_matrix):
    r_values = np.linspace(0, 2, num_samples)  # arbitrary range [0,2]
    bin_matrix = np.digitize(r_matrix, r_values)
    p_values = np.zeros(r_values.shape)
    for b in range(num_samples):
        bin_contributors = data_matrix[bin_matrix == b]
        p_values[b] = np.mean(bin_contributors) if len(bin_contributors) > 0 else None
    # interpolate bins with 'None' with values from neighbors
    nans = np.isnan(p_values)
    p_values[nans] = np.interp(r_values[nans], r_values[~nans], p_values[~nans], left=0.0, right=0.0)
    return r_values, p_values


if __name__ == '__main__':
    #
    # read the images
    #
    images = []
    for i in range(16):
        filename = '/home/cester/git/actilib/src/actilib/resources/dicom/nps/{:04d}_nps.dcm'.format(162-i)
        dicom_data = dcmread(filename)
        images.append(apply_modality_lut(dicom_data.pixel_array, dicom_data))
    pixel_size_xy_mm = np.array(dicom_data.PixelSpacing)
    image_size_xy_px = np.array([len(images[0]), len(images[0][0])])
    image_center_xy_px, section_radius_px = find_phantom_center_and_radius(images[0])

    # print('Diameter [mm]:', section_radius_px * 2 * pixel_size_xy_mm)

    # print(image_size_xy_px, image_center_xy_px, pixel_size_xy_mm)

    #
    # create and visualize the ROIs
    #
    roi_diameter_px = NPS_ROI_DIAMETER_MM / pixel_size_xy_mm[0]
    roi_distcent_px = NPS_ROI_DISTCENT_MM / pixel_size_xy_mm[0]
    rois = create_circle_of_rois(8, roi_diameter_px, roi_distcent_px, image_center_xy_px[0], image_center_xy_px[1])

    #fig, ax = plt.subplots()
    #ax.imshow(images[0], cmap=plt.cm.bone, vmin=-255, vmax=255)
    #import matplotlib.patches as patches
    #for roi in rois:
    #    x = roi.edge_l()
    #    y = roi.edge_t()
    #    rect = patches.Rectangle((x, y), roi.size(), roi.size(), linewidth=1, edgecolor='r', facecolor='none')
    #    ax.add_patch(rect)
    #plt.show()

    #
    # loop on the ROIs, extract the pixels and calculate the ROI values
    #
    num_samples = 128
    fft_size = [num_samples, num_samples]  # size of the FFT field
    hu_values = []
    nps_series = []
    for i_roi, roi in enumerate(rois):
        [y1, y2, x1, x2] = roi.yx_indexes()
        for i_image, image in enumerate(images):
            roi_pixels = image[y1-1:y2, x1-1:x2]  # (!) in "numpy images" the 1st coordinate is y
            # do stuff with the ROI pixels
            hu = np.mean(roi_pixels)
            hu_values.append(hu)
            # subtract mean value
            roi_sub = subtract_2d_poly_mean(roi_pixels)
            val = np.abs(np.fft.fftshift(np.fft.fftn(roi_sub, fft_size))) ** 2
            nps_series.append(val)
    # applying formula for 2D NPS
    norm = np.prod(pixel_size_xy_mm)/(rois[0].size()**2)
    nps_2d = norm * np.mean(np.array(nps_series), axis=0)
    # radial average of 2D NPS
    fx = fft_frequencies(fft_size[0], pixel_size_xy_mm[0])
    fy = fft_frequencies(fft_size[1], pixel_size_xy_mm[1])
    mesh_fx, mesh_fy = np.meshgrid(fx, fy)
    _, fr = cart2pol(mesh_fx, mesh_fy)
    nps_f, nps_1d = radial_profile(fr, nps_2d)
    print(nps_1d)
    # plotting
    plt.imshow(nps_2d, cmap=plt.cm.bone)
    plt.show()
    plt.plot(nps_f, nps_1d)
    plt.show()

