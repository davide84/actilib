from enum import Enum
import numpy as np


HUMIN = -999
HUMAX = 24000


# SEGMENTATION_MATERIALS
# the elements are ordered by HU values to visually inspect segmented images
class SegMats(Enum):
    AIR = 0
    LUNGS = 1
    FAT = 2
    SOFT_TISSUE = 3
    BONE = 4
    METAL = 5
    CUSTOM = 999


MAT_NAMES = {
    SegMats.AIR: 'Air',
    SegMats.LUNGS: 'Lungs',
    SegMats.FAT: 'Adipose tissue',
    SegMats.SOFT_TISSUE: 'Soft tissue',
    SegMats.BONE: 'Bone tissue',
    SegMats.METAL: 'Metal (experimental)',
    SegMats.CUSTOM: 'Custom'
}

HU_RANGES = {
    SegMats.AIR: [HUMIN, -800],
    SegMats.LUNGS: [-800, -300],
    SegMats.FAT: [-300, 0],
    SegMats.SOFT_TISSUE: [0, 150],
    SegMats.BONE: [300, 1000],
    SegMats.METAL: [1000, HUMAX],
    SegMats.CUSTOM: [128000, 128000]  # so that it never appears with default values
}

HU_RANGES_BY_NAME = {MAT_NAMES[k]: v for k, v in HU_RANGES.items()}


def get_default_segmentation_thresholds():
    return HU_RANGES


def segment_with_thresholds(pixel_image, hu_ranges=HU_RANGES):
    segm = -np.ones(pixel_image.shape)  # -1 does not correspond to any material
    for tissue, hu_range in hu_ranges.items():
        segm[(hu_range[0] < pixel_image) & (pixel_image < hu_range[1])] = tissue.value
    return segm
