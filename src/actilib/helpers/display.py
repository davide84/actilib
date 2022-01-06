import matplotlib.pyplot as plt
import matplotlib.patches as patches


def show_current_image():
    plt.show()


def display_pixels(pixels, flag_show=True):
    fig, ax = plt.subplots()
    fig.set_size_inches(18.5, 10.5)
    plt.tight_layout()
    ax.imshow(pixels, cmap=plt.cm.bone)
    if flag_show:
        plt.show()
    return fig, ax


def display_image(image, flag_show=True):
    return display_pixels(image['window'], flag_show)


def add_circle_on_image(ax, center_x, center_y, radius, color='r'):
    ax.add_patch(patches.Circle((center_x, center_y), radius, linewidth=1, edgecolor=color, fill=False))


def add_square_on_image(ax, left_x, top_y, size_x, size_y, color='r'):
    ax.add_patch(patches.Rectangle((left_x, top_y), size_x, size_y, linewidth=1, edgecolor=color, fill=False))


def display_image_with_rois(image, rois, flag_show=True):
    fig, ax = display_image(image, False)
    for roi in rois:
        if roi.shape() == 'square':
            add_square_on_image(ax, roi.edge_l(), roi.edge_t(), roi.size(), roi.size())
        elif roi.shape() == 'circular':
            add_circle_on_image(ax, roi.center_x(), roi.center_y(), roi.size()/2)
    if flag_show:
        plt.show()





