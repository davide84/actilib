import matplotlib.pyplot as plt
import matplotlib.patches as patches


def show_current_image():
    plt.show()


def display_image(pixel_array, flag_show=True):
    fig, ax = plt.subplots()
    fig.set_size_inches(18.5, 10.5)
    plt.tight_layout()
    ax.imshow(pixel_array, cmap=plt.cm.bone)
    if flag_show:
        plt.show()
    return fig, ax


def add_circle_on_image(ax, center_x, center_y, radius, color='r'):
    ax.add_patch(patches.Circle((center_x, center_y), radius, linewidth=1, edgecolor=color, fill=False))


def add_square_on_image(ax, left_x, top_y, size_x, size_y, color='r'):
    ax.add_patch(patches.Rectangle((left_x, top_y), size_x, size_y, linewidth=1, edgecolor=color, fill=False))


def display_image_with_rois(pixel_array, rois, flag_show=True):
    if not isinstance(rois, list):
        rois = [rois]
    fig, ax = display_image(pixel_array, False)
    for roi in rois:
        if roi.shape() == 'square':
            add_square_on_image(ax, roi.edge_l(), roi.edge_t(), roi.side(), roi.side())
        elif roi.shape() == 'circle':
            add_circle_on_image(ax, roi.center_x(), roi.center_y(), roi.radius())
    if flag_show:
        plt.show()





