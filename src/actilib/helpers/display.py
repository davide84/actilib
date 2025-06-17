import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pydicom.pixel_data_handlers.util import apply_windowing


def show_current_image():
    plt.show()


def display_image(pixel_array, flag_show=True, dicom_header=None, cmap='gray'):
    fig, ax = plt.subplots()
    # fig.set_size_inches(18.5, 10.5)
    plt.tight_layout()
    if dicom_header is None:
        ax.imshow(pixel_array, cmap=cmap)
    else:
        ax.imshow(apply_windowing(pixel_array, dicom_header), cmap=cmap)
    if flag_show:
        plt.show()
    return fig, ax


def add_circle_on_image(ax, center_x, center_y, radius, color='r'):
    return ax.add_patch(patches.Circle((center_x, center_y), radius, linewidth=1, edgecolor=color, fill=False))


def add_square_on_image(ax, left_x, top_y, size_x, size_y, color='r'):
    return ax.add_patch(patches.Rectangle((left_x, top_y), size_x, size_y, linewidth=1, edgecolor=color, fill=False))


def add_roi_on_image(ax, roi, color='r'):
    if roi.shape() == 'square':
        return add_square_on_image(ax, roi.edge_l(), roi.edge_t(), roi.side(), roi.side(), color)
    elif roi.shape() == 'circle':
        return add_circle_on_image(ax, roi.center_x(), roi.center_y(), roi.radius(), color)
    return None


def display_image_with_rois(pixel_array, rois, flag_show=True, dicom_header=None, cmap='bone'):
    if not isinstance(rois, list):
        rois = [rois]
    fig, ax = display_image(pixel_array, False, dicom_header=dicom_header, cmap=cmap)
    for roi in rois:
        add_roi_on_image(ax, roi)
    if flag_show:
        plt.show()
    return fig, ax


