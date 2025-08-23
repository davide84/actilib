import numpy as np
from scipy.ndimage import generic_filter
from scipy.signal import convolve2d
from numpy.lib.stride_tricks import sliding_window_view
from actilib.analysis.segmentation import SegMats, get_default_segmentation_thresholds, segment_with_thresholds

"""
GLN - Global Noise Level
Implementation bases on Christianson et al., 'Automated Technique to Measure Noise in Clinical CT Examinations' (2015)
doi: 10.2214/AJR.14.13613
This function takes a single DICOM image (including headers) as input and calculates its GNL.
"""


def get_histogram_mode(data):
    histo_max = int(np.nanmax(data) + 1)
    histogram, bin_edges = np.histogram(data, bins=histo_max, range=(1, histo_max))
    return np.argmax(histogram)  # bin size = 1 -> bin index = bin upper edge = x value


def calculate_local_std(img, kernel_size, algorithm):
    kernel_shape = (kernel_size, kernel_size)
    if 'generic_filter' == algorithm:  # probably the most accurate, but slow
        img_std = generic_filter(img, np.std, size=kernel_size)
    elif 'convolution' == algorithm:  # almost the fastest and handles the boundaries
        kernel = np.ones(kernel_shape) / (kernel_size ** 2)
        mean_of_sq = convolve2d(img ** 2, kernel, mode='same', boundary='symm')
        sq_of_mean = convolve2d(img, kernel, mode='same', boundary='symm') ** 2
        img_std = np.sqrt(mean_of_sq - sq_of_mean)
    elif 'sliding_window_view' == algorithm:  # 30% fastest as convolution, but must be padded
        margin = int((kernel_size - 1) / 2)
        img_pad = np.full((margin + margin + img.shape[0], margin + margin + img.shape[1]), np.nan)
        img_pad[margin:-margin, margin:-margin] = img
        img_std = sliding_window_view(img_pad, window_shape=kernel_shape).std(axis=(2, 3))
    else:
        raise NotImplementedError('algorithm "' + algorithm + '"')
    return img_std


def calculate_gnl(dicom_images, tissues=SegMats.SOFT_TISSUE, kernel_radius_mm=3,
                  hu_ranges=get_default_segmentation_thresholds(),
                  return_plot_data=False, mask_rois=None,
                  algorithm='convolution'):
    # input preparation
    if not isinstance(dicom_images, list):
        dicom_images = [dicom_images]
    if not isinstance(tissues, list):
        tissues = [tissues]
    # calculation
    gnls = []
    for dicom_image in dicom_images:
        pixels = dicom_image['pixels']
        # 0. masking ROIs (e.g. image numbers, arrows...)
        if mask_rois is not None:
            if not isinstance(mask_rois, list):
                mask_rois = [mask_rois]
            for roi in mask_rois:
                pixels[roi[0]:roi[1], roi[2]:roi[3]] = roi[4]
        # 1. threshold-based segmentation
        segmap = segment_with_thresholds(pixels, hu_ranges)
        # 2. calculation of local SD - kernel has always an odd number of pixels
        kernel_size_px = 1 + np.round(2 * kernel_radius_mm / dicom_image['header'].PixelSpacing[0]).astype(int)
        if [None] != tissues:
            gnlmap = np.zeros(segmap.shape)
            for tissue in tissues:
                img_segm = np.where(segmap == tissue.value, pixels, 0)
                img_gnl = calculate_local_std(img_segm, kernel_size_px, algorithm)
                gnlmap = np.where(segmap == tissue.value, img_gnl, gnlmap)
        else:
            gnlmap = calculate_local_std(img_segm, kernel_size_px, algorithm)
        # 3. histogram of local SD and mode
        gnls.append(get_histogram_mode(gnlmap))
        if return_plot_data:
            return np.mean(gnls), np.std(gnls), pixels, segmap, gnlmap
    return np.mean(gnls), np.std(gnls)
