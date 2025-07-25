import numpy as np
from scipy.ndimage import generic_filter
from actilib.analysis.segmentation import SegMats, get_default_segmentation_thresholds, segment_with_thresholds


"""
GLN - Global Noise Level
Implementation bases on Christianson et al., 'Automated Technique to Measure Noise in Clinical CT Examinations' (2015)
doi: 10.2214/AJR.14.13613
This function takes a single DICOM image (including headers) as input and calculates its GNL.
"""


def calculate_gnl(dicom_images, tissues=SegMats.SOFT_TISSUE, kernel_size_mm=6,
                  hu_ranges=get_default_segmentation_thresholds()):
    # input preparation
    if not isinstance(dicom_images, list):
        dicom_images = [dicom_images]
    if not isinstance(tissues, list):
        tissues = [tissues]
    # calculation
    gnls = []
    for dicom_image in dicom_images:
        pixels = dicom_image['pixels']
        # 1. threshold-based segmentation
        img_segm = segment_with_thresholds(pixels, hu_ranges)
        # 2. calculation of local SD
        kernel_size_px = np.round(kernel_size_mm / dicom_image['header'].PixelSpacing[0]).astype(int)
        img_noise = generic_filter(pixels, np.std, size=kernel_size_px)
        if [None] != tissues:
            img_gnl = np.zeros_like(img_noise)
            for tissue in tissues:
                img_gnl = np.where(img_segm == tissue.value, img_noise, img_gnl)
        else:
            img_gnl = img_noise
        # from actilib.helpers.display import display_image  # DEBUG
        # display_image(np.log(1 + img_gnl), cmap='jet')  # DEBUG
        # 3. histogram of local SD and mode
        histo_max = int(np.max(img_gnl) + 1)
        histogram, bin_edges = np.histogram(img_gnl, bins=histo_max, range=(1, histo_max))
        gnls.append(np.argmax(histogram))  # bin size = 1 -> bin index = bin upper edge = x value
    return np.mean(gnls), np.std(gnls)
