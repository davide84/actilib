import numpy as np
# from scipy.ndimage import generic_filter
from numpy.lib.stride_tricks import sliding_window_view
from actilib.analysis.segmentation import SegMats, get_default_segmentation_thresholds, segment_with_thresholds

"""
GLN - Global Noise Level
Implementation bases on Christianson et al., 'Automated Technique to Measure Noise in Clinical CT Examinations' (2015)
doi: 10.2214/AJR.14.13613
This function takes a single DICOM image (including headers) as input and calculates its GNL.
"""


def calculate_gnl(dicom_images, tissues=SegMats.SOFT_TISSUE, kernel_size_mm=6,
                  hu_ranges=get_default_segmentation_thresholds(),
                  no_noise_value=np.nan, return_plot_data=False, mask_rois=None):
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
        # 2. calculation of local SD
        kernel_size_px = np.round(kernel_size_mm / dicom_image['header'].PixelSpacing[0]).astype(int)
        if [None] != tissues:
            gnlmap = np.full(segmap.shape, no_noise_value)
            for tissue in tissues:
                img_segm = np.where(segmap == tissue.value, pixels, np.nan)
                # two different implementations, sliding_window_view is >6 times faster
                # img_gnl = generic_filter(img_segm, np.nanstd, size=kernel_size_px)
                img_gnl = np.nanstd(sliding_window_view(img_segm, window_shape=(kernel_size_px, kernel_size_px)))
                gnlmap = np.where(segmap == tissue.value, img_gnl, gnlmap)
        else:
            gnlmap = np.nanstd(sliding_window_view(pixels, window_shape=(kernel_size_px, kernel_size_px)))
        # 3. histogram of local SD and mode
        histo_max = int(np.nanmax(gnlmap) + 1)
        histogram, bin_edges = np.histogram(gnlmap, bins=histo_max, range=(1, histo_max))
        gnls.append(np.argmax(histogram))  # bin size = 1 -> bin index = bin upper edge = x value
        if return_plot_data:
            return np.mean(gnls), np.std(gnls), pixels, segmap, gnlmap
    return np.mean(gnls), np.std(gnls)
