from actilib.helpers.io import load_image_from_path
from actilib.analysis.segmentation import SegMats
from actilib.analysis.gnl import calculate_gnl

# image = load_image_from_path('/home/cester/Data/CBCT_Lungs/CBCT Manual/Best quality 100kVp 5mA/00000100.dcm')
# image['pixels'][0:15, 0:10] = -1000
# gnl = calculate_gnl(image, SegMats.LUNGS, hu_ranges={SegMats.LUNGS:[-700,-200]})
# print(gnl)

image = load_image_from_path('/home/cester/Data/CBCT Spine/Rearranged/CBCT_17x47e_1mm/Bestquality_100kVp_75mA_11.52s_4.81mGy/0400.dcm')
gnl1, gnl2, pixels, segm, figure = calculate_gnl(image, SegMats.SOFT_TISSUE, return_plot_data=True, mask_rois=[(0,20,0,20,-1000)], no_noise_value=0)
print(gnl1, gnl2)

import matplotlib.pyplot as plt
import numpy as np

mask = np.where(segm == SegMats.SOFT_TISSUE.value, segm, np.zeros_like(segm))
print(np.unique(segm))
print(np.unique(mask))
fig, axs = plt.subplots(1, 4, figsize=(12, 7))
axs[0].imshow(pixels, cmap='gray', interpolation='nearest')
axs[1].imshow(mask, cmap='gray', interpolation='nearest')
# axs[1].imshow(mask, cmap='tab10')
axs[2].imshow(figure, cmap='nipy_spectral', interpolation='nearest')
img = axs[3].imshow(figure, cmap='nipy_spectral', interpolation='nearest')
plt.colorbar(img, orientation='horizontal', shrink=0.75)
for i in range(3):
    axs[i].set_xticks([])
    axs[i].set_yticks([])
plt.tight_layout()
plt.show()

