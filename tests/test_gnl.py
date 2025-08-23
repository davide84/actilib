from actilib.helpers.io import load_image_from_path
from actilib.analysis.segmentation import SegMats
from actilib.analysis.gnl import calculate_gnl

# image = load_image_from_path('/home/cester/Data/CBCT_Lungs/CBCT Manual/Best quality 100kVp 5mA/00000100.dcm')
# image['pixels'][0:15, 0:10] = -1000
# gnl = calculate_gnl(image, SegMats.LUNGS, hu_ranges={SegMats.LUNGS:[-700,-200]})
# print(gnl)

image = load_image_from_path('/home/cester/Data/Paper - HAND/Rearranged/EICT - Hand - MPR - 1.0mm/00000160.dcm')

import matplotlib.pyplot as plt
from time import time

fig, axs = plt.subplots(3, 2, figsize=(8, 8))
gnlmap = [None, None, None]
for a, algorithm in enumerate(['generic_filter', 'convolution', 'sliding_window_view']):
    time_start = time()
    gnl1, gnl2, pixels, segmap, gnlmap[a] = calculate_gnl(dicom_images=image,
                                                          tissues=SegMats.AIR,
                                                          return_plot_data=True,
                                                          # mask_rois=[(0,20,0,20,-1000)],
                                                          algorithm=algorithm)
    title = '{} ({:.1f} s) GNL = {}'.format(algorithm, time() - time_start, gnl1)
    print(title)
    axs[a, 0].set_title(title)
    img = axs[a, 0].imshow(gnlmap[a], cmap='nipy_spectral', interpolation='nearest')
    plt.colorbar(img, orientation='horizontal', shrink=0.75)
    img = axs[a, 1].imshow(gnlmap[a]-gnlmap[0], cmap='nipy_spectral', interpolation='nearest')
    plt.colorbar(img, orientation='horizontal', shrink=0.75)
    axs[a, 0].set_xticks([])
    axs[a, 0].set_yticks([])
    axs[a, 1].set_xticks([])
    axs[a, 1].set_yticks([])
    plt.tight_layout()
    plt.savefig('compare.png')
