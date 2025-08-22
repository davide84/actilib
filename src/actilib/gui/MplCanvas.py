from pydicom.pixel_data_handlers.util import apply_modality_lut
from pydicom.pixel_data_handlers import apply_windowing
from PyQt5.QtCore import pyqtSignal
from pathlib import Path
from math import floor
import pydicom
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.cm import ScalarMappable
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from actilib.helpers.io import load_image_from_path

LOAD_RECURSION_LIMIT = 1  # 0 = dragged files only, 1 = files inside directory, 2 = directories inside directory...
PATCH_ZORDER_DEFAULT = 1.0
PATCH_ZORDER_HIGHLIGHT = 2.0
ROI_COLOR_DEFAULT = 'r'
ROI_COLOR_HIGHLIGHT = 'g'


class MplCanvas(FigureCanvasQTAgg):

    image_loaded = pyqtSignal(int)
    cursor_on_image = pyqtSignal(int, int, int)
    scroll_event = pyqtSignal(str)

    def __init__(self, parent=None, width=5, height=5.5, hide_ticks=False):
        self.slider = None
        self.image_paths = []
        self.image_pixels = []
        self.fig, self.axes = plt.subplots(nrows=2, height_ratios=[10, 1], figsize=(width, height))
        super(MplCanvas, self).__init__(self.fig)
        self.mpl_connect('motion_notify_event', self.emit_current_image_coordinates)
        self.mpl_connect('scroll_event', self.emit_scroll_event)
        self.fig.subplots_adjust(left=0.05, right=0.99, top=0.99, bottom=0.05)
        self.current_image = None
        self.hide_image_ticks = hide_ticks
        self.roi_patches = []
        self.roi_active = None
        self.reset_axes()
        self.array_shown = np.zeros((256, 256))
        self.image_shown = self.axes[0].imshow(self.array_shown, cmap='gray')

    def reset_axes(self):
        for ax in self.axes:
            ax.clear()
        self.axes[1].axis('off')
        if self.hide_image_ticks:
            self.axes[0].set_xticks([])
            self.axes[0].set_yticks([])

    @staticmethod
    def _patch_from_roi(roi, color=ROI_COLOR_DEFAULT, zorder=PATCH_ZORDER_DEFAULT):
        if roi.shape() == 'square':
            return patches.Rectangle((roi.edge_l(), roi.edge_t()), roi.side(), roi.side(),
                                     linewidth=1, edgecolor=color, fill=False, zorder=zorder)
        elif roi.shape() == 'circle':
            return patches.Circle((roi.center_x(), roi.center_y()), roi.radius(),
                                  linewidth=1, edgecolor=color, fill=False, zorder=zorder)
        else:
            raise NotImplemented(roi.shape())

    def add_roi(self, roi, color=ROI_COLOR_DEFAULT):
        self.roi_patches.append(self._patch_from_roi(roi, color))
        self.axes[0].add_patch(self.roi_patches[-1])

    def replace_roi(self, index, roi, color=ROI_COLOR_DEFAULT, zorder=PATCH_ZORDER_DEFAULT):
        patch = self._patch_from_roi(roi, color, zorder)
        self.roi_patches[index] = patch
        self.redraw_rois()

    def redraw_rois(self):
        for patch in self.axes[0].patches:
            patch.remove()
        for patch in self.roi_patches:
            self.axes[0].add_patch(patch)

    def clear_rois(self):
        self.roi_patches = []
        self.redraw_rois()

    def highlight_roi(self, index):
        try:
            self.roi_patches[index].set(color=ROI_COLOR_HIGHLIGHT, zorder=PATCH_ZORDER_HIGHLIGHT)
            if self.roi_active is not None and self.roi_active != index:
                self.roi_patches[self.roi_active].set(color=ROI_COLOR_DEFAULT, zorder=PATCH_ZORDER_DEFAULT)
            self.roi_active = index
        except IndexError:
            pass
        self.draw()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("text/plain") and event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        self.recursively_validate_and_load_files(files)

    def recursively_validate_and_load_files(self, file_list, recursion_level=0):
        validated_paths = []
        for f in sorted(file_list):
            file_path = Path(f)
            if file_path.is_dir() and recursion_level < LOAD_RECURSION_LIMIT:
                validated_paths += self.recursively_validate_and_load_files(file_path.glob('*'), recursion_level+1)
            elif file_path.is_file():
                # check if can be parsed by pydicom
                try:
                    pydicom.dcmread(file_path, stop_before_pixels=True)
                    validated_paths.append(str(file_path))
                except pydicom.errors.InvalidDicomError:
                    pass  # not a proper DICOM file
        if validated_paths:
            self.image_paths = validated_paths
            self.image_pixels = [None] * len(validated_paths)
            self.image_loaded.emit(len(validated_paths))
        return validated_paths

    def show_image(self, array_index, hu_window=None, alpha=1.0):
        if array_index > len(self.image_paths) - 1:
            return None
        try:
            if self.image_pixels[array_index] is None:
                self.current_image = load_image_from_path(self.image_paths[array_index])
                self.image_pixels[array_index] = self.current_image['pixels']
                self.array_shown = self.image_pixels[array_index]
            self.reset_axes()
            img_to_show = self.image_pixels[array_index]
            if hu_window is None:
                self.image_shown = self.axes[0].imshow(img_to_show, cmap='gray', alpha=alpha)
            else:
                vmin = hu_window['C'] - hu_window['W']
                vmax = hu_window['C'] + hu_window['W']
                self.image_shown = self.axes[0].imshow(img_to_show, cmap='gray', alpha=alpha, vmin=vmin, vmax=vmax)
            self.draw()
            return array_index
        except IndexError as e:
            print(e)
        return None

    def show_overlay(self, pixels, alpha=0.5, cmap='gray'):
        ret = self.axes[0].imshow(pixels, alpha=alpha, cmap=cmap)
        self.draw()
        return ret

    def show_colorbar(self, img):
        sm = ScalarMappable(cmap=img.cmap, norm=img.norm)
        self.fig.colorbar(sm, orientation='horizontal', cax=self.axes[1], location='top')
        self.axes[1].axis('on')
        self.axes[1].set_yticks([])
        self.axes[1].xaxis.set_ticks_position('bottom')
        self.axes[1].set_xlabel('GNL scale [HU]')
        self.draw()

    def get_current_image(self):
        return self.current_image

    def emit_current_image_coordinates(self, event):
        if event.inaxes == self.axes[0]:
            x = floor(event.xdata)
            y = floor(event.ydata)
            z = int(self.array_shown[y, x])
            self.cursor_on_image.emit(x, y, z)

    def emit_scroll_event(self, event):
        if event.inaxes == self.axes[0]:
            self.scroll_event.emit(event.button)
