from enum import Enum
import numpy as np


# SEGMENTATION_MATERIALS
# the elements are ordered by HU values to visually inspect segmented images
class SegMats(Enum):
    AIR = -1
    UNSEGMENTED = 0  # defined as zero so np.zeros() initializes to UNSEGMENTED
    LUNGS = 1
    FAT = 2
    SOFT_TISSUE = 3
    BONE = 4
    METAL = 5  # placeholder


HU_RANGES = {
    SegMats.AIR: [-999, -800],  # let's explicitly exclude -1000 which will stay UNSEGMENTED
    SegMats.LUNGS: [-800, -300],
    SegMats.FAT: [-300, 0],
    SegMats.SOFT_TISSUE: [0, 150],
    SegMats.BONE: [300, 1000],
    SegMats.METAL: [1000, 24000]
}


def get_default_segmentation_thresholds():
    return HU_RANGES


def segment_with_thresholds(pixel_image, hu_ranges=None):
    if hu_ranges is None:
        hu_ranges = HU_RANGES
    segm = np.zeros(pixel_image.shape)
    for tissue, hu_range in hu_ranges.items():
        segm[(hu_range[0] < pixel_image) & (pixel_image < hu_range[1])] = tissue.value
    return segm
