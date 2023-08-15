import json

import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QSlider, QStatusBar, QHBoxLayout, QVBoxLayout,
                             QDesktopWidget, QPushButton, QFileDialog, QHeaderView, QTableView, QStyle)
from pathlib import Path
from PyQt5.QtCore import Qt, pyqtSignal
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from actilib.helpers.rois import CircleROI, SquareROI
from actilib.gui.TableModel import ROITableModel
import pydicom
from pydicom.pixel_data_handlers.util import apply_modality_lut
from pydicom.pixel_data_handlers import apply_windowing


LOAD_RECURSION_LIMIT = 1  # 0 = dragged files only, 1 = files inside directory, 2 = directories inside directory...
PATCH_ZORDER_DEFAULT = 1.0
PATCH_ZORDER_HIGHLIGHT = 2.0
ROI_COLOR_DEFAULT = 'r'
ROI_COLOR_HIGHLIGHT = 'g'


class MplCanvas(FigureCanvasQTAgg):

    image_loaded = pyqtSignal(int)

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.slider = None
        self.image_paths = []
        self.image_array = []
        self.fig = plt.Figure(figsize=(width, height), dpi=dpi)
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


def roi_from_row(row):
    if row[1] == 'Square':
        return SquareROI(row[4], row[2], row[3])
    elif row[1] == 'Circle':
        return CircleROI(row[4] / 2.0, row[2], row[3])
    raise ValueError


class RoiCreator(QMainWindow):
    def __init__(self):
        super(RoiCreator, self).__init__()

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        self.canvas = MplCanvas()
        self.roimodel = ROITableModel()
        self.roitable = QTableView()
        self.roitable.setModel(self.roimodel)

        self.drag_callback_id = None
        self.drag_start_xy = None
        self.drag_roi_cxcy = None

        self.setGeometry(50, 50, 1300, 800)
        self.setWindowTitle("ROI Creator")
        #self.setWindowIcon(QIcon(resource_filename('isi.resources', 'templogo.jpg')))
        self.draw_ui()
        self.center()
        self.show()

    def center(self):
        qr = self.frameGeometry()  # geometry of the main window
        cp = QDesktopWidget().availableGeometry().center()  # center point of screen
        qr.moveCenter(cp)  # move rectangle's center point to screen's center point
        self.move(qr.topLeft())  # top left of rectangle becomes top left of window centering it

    def roi_current_index(self):
        try:
            return self.roitable.selectedIndexes()[0].row()
        except IndexError:
            return None

    def mouse_is_over_selected_roi(self, event):
        row = self.roimodel.getRowData(self.roi_current_index())
        return -row[4] / 2.0 < event.xdata - row[2] < + row[4] / 2.0 and -row[4] / 2.0 < event.ydata - row[3] < row[
            4] / 2.0

    def roi_mouse_stop_drag(self, event):
        self.canvas.mpl_disconnect(self.drag_callback_id)

    def roi_mouse_start_drag(self, event):
        roi_index = self.roi_current_index()
        if roi_index is None:
            return
        row = self.roimodel.getRowData(roi_index)
        if self.mouse_is_over_selected_roi(event):
            self.drag_start_xy = (event.xdata, event.ydata)
            self.drag_roi_cxcy = (row[2], row[3])
            self.drag_callback_id = self.canvas.mpl_connect('motion_notify_event', self.roi_mouse_drag)
            self.canvas.mpl_connect('button_release_event', self.roi_mouse_stop_drag)

    def roi_mouse_drag(self, event):
        delta_x = int(event.xdata - self.drag_start_xy[0])
        delta_y = int(event.ydata - self.drag_start_xy[1])
        roi_index = self.roi_current_index()
        self.roimodel.setData(self.roimodel.index(roi_index, 2), self.drag_roi_cxcy[0] + delta_x, Qt.EditRole)
        self.roimodel.setData(self.roimodel.index(roi_index, 3), self.drag_roi_cxcy[1] + delta_y, Qt.EditRole)

    def roi_mouse_resize(self, event):
        roi_index = self.roi_current_index()
        if roi_index is None or not self.mouse_is_over_selected_roi(event):
            if event.button == 'up':
                self.slider.setValue(min(self.slider.value() + 1, self.slider.maximum()))
            elif event.button == 'down':
                self.slider.setValue(max(self.slider.value() - 1, self.slider.minimum()))
        else:
            row = self.roimodel.getRowData(roi_index)
            if event.button == 'up':
                self.roimodel.setData(self.roimodel.index(roi_index, 4), row[4] + 2, Qt.EditRole)
            elif event.button == 'down':
                self.roimodel.setData(self.roimodel.index(roi_index, 4), row[4] - 2, Qt.EditRole)

    def draw_ui(self):
        lay_h_main = QHBoxLayout()
        central_widget = QWidget()
        central_widget.setLayout(lay_h_main)
        self.setCentralWidget(central_widget)
        #
        # left panel: image display
        #
        lay_h_images = QHBoxLayout()
        # slider
        self.slider = QSlider(Qt.Vertical)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)
        self.slider.valueChanged.connect(self.select_image)
        lay_h_images.addWidget(self.slider)
        # canvas
        self.canvas.image_loaded.connect(self.update_slider_maximum)
        lay_h_images.addWidget(self.canvas)
        lay_h_main.addLayout(lay_h_images, 67)
        # self.canvas.mpl_connect('motion_notify_event', self.react)
        self.canvas.mpl_connect('button_press_event', self.roi_mouse_start_drag)
        self.canvas.mpl_connect('scroll_event', self.roi_mouse_resize)
        self.canvas.setAcceptDrops(True)
        #
        # right panel: ROI operations
        #
        lay_v_rois = QVBoxLayout()
        lay_h_main.addLayout(lay_v_rois, 33)
        # ROI buttons
        lay_h_roibtns = QHBoxLayout()
        btn_roi_add = QPushButton(' Add Square ROI')
        btn_roi_add.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_FileIcon')))
        btn_roi_add.clicked.connect(lambda: self.roi_add('Square'))
        lay_h_roibtns.addWidget(btn_roi_add)
        btn_roi_add = QPushButton(' Add Circle ROI')
        btn_roi_add.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_FileIcon')))
        btn_roi_add.clicked.connect(lambda: self.roi_add('Circle'))
        lay_h_roibtns.addWidget(btn_roi_add)
        btn_roi_del = QPushButton(' Delete ROI')
        btn_roi_del.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_TrashIcon')))
        btn_roi_del.clicked.connect(self.roi_remove_selected)
        lay_h_roibtns.addWidget(btn_roi_del)
        btn_roi_sav = QPushButton(' Save ROIs...')
        btn_roi_sav.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_DialogSaveButton')))
        btn_roi_sav.clicked.connect(self.roi_save_list)
        lay_h_roibtns.addWidget(btn_roi_sav)
        lay_v_rois.addLayout(lay_h_roibtns)
        # ROI table
        self.roitable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.roitable.verticalHeader().setVisible(True)
        self.roitable.verticalHeader().setFixedWidth(20)
        # self.roitable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # self.roitable.clicked.connect(lambda: print(self.roitable.selectedIndexes()[0].row()))
        # self.roimodel.layoutChanged.connect(self.roi_redraw_all)  # added or removed ROI
        self.roimodel.dataChanged.connect(self.roi_update_current)  # changed ROI
        self.roitable.clicked.connect(self.roi_highlight_selected)  # selected another ROI
        lay_v_rois.addWidget(self.roitable)

    def display_new_image_index(self):
        self.statusBar.showMessage('Slice {} of {} - {}'.format(self.slider.value() + 1, self.slider.maximum() + 1,
                                   self.canvas.image_paths[self.slider.value()]))

    def update_slider_maximum(self, new_max):
        self.slider.setMaximum(new_max)
        self.display_new_image_index()

    def select_image(self):
        image_index = self.canvas.show_image(self.slider.value())
        if image_index is not None:
            self.display_new_image_index()

    def roi_redraw_all(self):
        self.canvas.clear_rois()
        for r in range(self.roimodel.rowCount(0)):
            self.canvas.add_roi(roi_from_row(self.roimodel.getRowData(r)))
        self.roi_highlight_selected()

    def roi_remove_selected(self):
        try:
            self.roimodel.removeRow(self.roi_current_index())
            self.roi_redraw_all()
        except IndexError:
            pass

    def roi_update_current(self):
        roi_index = self.roi_current_index()
        new_roi = roi_from_row(self.roimodel.getRowData(roi_index))
        self.canvas.replace_roi(roi_index, new_roi)
        self.roi_highlight_selected()

    def roi_highlight_selected(self):
        self.canvas.highlight_roi(self.roi_current_index())

    def roi_add(self, shape):
        self.roimodel.addRow(shape)
        self.roitable.selectRow(self.roimodel.rowCount(0) - 1)
        self.canvas.add_roi(roi_from_row(self.roimodel.getRowData(self.roimodel.rowCount(0) - 1)))
        self.roi_highlight_selected()

    def roi_save_list(self):
        # prepare the data structure for writeout
        roi_out = []
        for r in range(self.roimodel.rowCount(0)):
            row = self.roimodel.getRowData(r)
            roi_out.append({
                'name': row[0],
                'shape': row[1],
                'center_x': row[2],
                'center_y': row[3],
                'size': row[4]
            })
        # select file and write
        fname = QFileDialog.getSaveFileName(self, 'Save file', '.', "JSON text file (*.json)")
        if fname != ('', ''):
            file_path = Path(fname[0] if isinstance(fname, tuple) else fname).with_suffix('.json')
            with open(file_path, 'w', encoding='utf-8') as fout:
                json.dump(roi_out, fout)


if __name__ == '__main__':
    app = QApplication([])
    roi_creator = RoiCreator()
    app.exec_()
