import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pydicom.pixel_data_handlers.util import apply_windowing


def plot_image_with_rois(image_pixels, dicom_header, rois):
    windowed_image = apply_windowing(image_pixels, dicom_header)
    fig, ax = plt.subplots()
    ax.imshow(windowed_image, cmap=plt.cm.bone)
    for roi in rois:
        if roi.shape() == 'square':
            ax.add_patch(patches.Rectangle((roi.edge_l(), roi.edge_t()), roi.size(), roi.size(),
                                           linewidth=1, edgecolor='r', facecolor='none'))
        elif roi.shape() == 'circular':
            ax.add_patch(patches.Circle((roi.center_x(), roi.center_y()), roi.size()/2,
                                        linewidth=1, edgecolor='r', fill=False))
    plt.show()





