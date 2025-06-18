from enum import Enum
import numpy as np
from actilib.helpers.io import load_image_from_path
from scipy.ndimage import generic_filter
# from actilib.helpers.display import display_image


"""
GLN - Global Noise Level
Implementation bases on Christianson et al., 'Automated Technique to Measure Noise in Clinical CT Examinations' (2015)
doi: 10.2214/AJR.14.13613
This function takes a single DICOM image (including headers) as input and calculates its GNL.
"""
# TODO: integrate this calculation in noise_properties(), averaging the GNL over multiple images if a list is provided


# SEGMENTATION_MATERIALS
# the elements are ordered by HU values to visually inspect segmented images
class Tissue(Enum):
    AIR = -1
    UNSEGMENTED = 0
    FAT = 1
    SOFT_TISSUE = 2
    BONE = 3


def segment_with_thresholds(pixel_image):
    segm = np.ones(pixel_image.shape) * Tissue.UNSEGMENTED.value  #
    segm[pixel_image < -800] = Tissue.AIR.value
    segm[(-300 <= pixel_image) & (pixel_image < 0)] = Tissue.FAT.value
    segm[(-0 <= pixel_image) & (pixel_image < 150)] = Tissue.SOFT_TISSUE.value
    segm[300 < pixel_image] = Tissue.BONE.value
    return segm


def calculate_gnl(dicom_images, tissue=Tissue.SOFT_TISSUE, kernel_size_mm=6):
    if not isinstance(dicom_images, list):
        dicom_images = [dicom_images]
    gnls = []
    for dicom_image in dicom_images:
        pixels = dicom_image['pixels']
        # 0. clip HU values to the minimum (sometimes we have -8192 at the corners)
        pixels[pixels < -1000] = -1000
        # 1. threshold-based segmentation
        segm = segment_with_thresholds(pixels)
        segm[segm != tissue.value] = 0
        # display_image(segm)  # DEBUG
        # 2. calculation of local SD
        kernel_size_px = np.round(kernel_size_mm / dicom_image['header'].PixelSpacing[0]).astype(int)
        sd_map = generic_filter(pixels, np.std, size=kernel_size_px)
        sd_map[segm != tissue.value] = 0
        # display_image(np.log(1 + sd_map), cmap='jet')  # DEBUG
        # 3. histogram of local SD and mode
        histo_max = int(np.max(sd_map) + 1)
        histogram, bin_edges = np.histogram(sd_map, bins=histo_max, range=(1, histo_max))
        gnls.append(np.argmax(histogram))  # bin size = 1 -> bin index = bin upper edge = x value
    return np.mean(gnls), np.std(gnls)
