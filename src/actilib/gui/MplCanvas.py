import pydicom
from pydicom.pixel_data_handlers.util import apply_modality_lut
from pydicom.pixel_data_handlers import apply_windowing
from PyQt5.QtCore import pyqtSignal
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

LOAD_RECURSION_LIMIT = 1  # 0 = dragged files only, 1 = files inside directory, 2 = directories inside directory...
PATCH_ZORDER_DEFAULT = 1.0
PATCH_ZORDER_HIGHLIGHT = 2.0
ROI_COLOR_DEFAULT = 'r'
ROI_COLOR_HIGHLIGHT = 'g'


class MplCanvas(FigureCanvasQTAgg):

    image_loaded = pyqtSignal(int)

    def __init__(self, parent=None, width=5, height=4):
        self.slider = None
        self.image_paths = []
        self.image_array = []
        self.fig = plt.Figure(figsize=(width, height))
        self.fig.subplots_adjust(left=0.05, right=0.99, top=0.99, bottom=0.05)
        self.axes = self.fig.add_subplot(111)
        self.image_shown = self.axes.imshow(np.zeros((256, 256)), cmap='gray')
        self.roi_patches = []
        self.roi_active = None
        super(MplCanvas, self).__init__(self.fig)

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
        self.axes.add_patch(self.roi_patches[-1])

    def replace_roi(self, index, roi, color=ROI_COLOR_DEFAULT, zorder=PATCH_ZORDER_DEFAULT):
        patch = self._patch_from_roi(roi, color, zorder)
        self.roi_patches[index] = patch
        self.redraw_rois()

    def redraw_rois(self):
        self.axes.patches.clear()
        for patch in self.roi_patches:
            self.axes.add_patch(patch)

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
        image_paths = self.recursively_validate_and_load_files(files)
        if image_paths:
            self.image_paths = image_paths
            self.image_array = [None] * len(image_paths)
            self.show_image(0)
            self.image_loaded.emit(len(image_paths)-1)

    def recursively_validate_and_load_files(self, file_list, recursion_level=0):
        file_load = []
        for f in file_list:
            file_path = Path(f)
            if file_path.is_dir() and recursion_level < LOAD_RECURSION_LIMIT:
                file_load += self.recursively_validate_and_load_files(file_path.glob('*'), recursion_level+1)
            elif file_path.is_file():
                # check if can be parsed by pydicom
                try:
                    pydicom.dcmread(file_path, stop_before_pixels=True)
                    file_load.append(str(file_path))
                except pydicom.errors.InvalidDicomError:
                    pass  # not a proper DICOM file
        return file_load

    def show_image(self, index):
        try:
            if self.image_array[index] is None:
                dicom = self.image_array[index] = pydicom.dcmread(self.image_paths[index])
                self.image_array[index] = apply_windowing(apply_modality_lut(dicom.pixel_array, dicom), dicom)
            if self.image_shown.get_array().shape == self.image_array[index].shape:
                self.image_shown.set_data(self.image_array[index])
                self.image_shown.autoscale()
            else:
                self.image_shown = self.axes.imshow(self.image_array[index], cmap='gray')
            self.draw()
            return index
        except IndexError as e:
            print(e)
        return None
