import json

import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QTabWidget, QMenuBar, QDialog,
                             QGridLayout, QHBoxLayout, QVBoxLayout, QGroupBox, QDateEdit, QTimeEdit, QDesktopWidget,
                             QPushButton, QLabel, QLineEdit, QPlainTextEdit, QFileDialog, QHeaderView, QCheckBox,
                             QTableView, QAbstractItemView, QStyle)
from pathlib import Path
from PyQt5.QtCore import Qt
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from actilib.helpers.rois import CircleROI, SquareROI
from actilib.gui.TableModel import ROITableModel


PATCH_ZORDER_DEFAULT = 1.0
PATCH_ZORDER_HIGHLIGHT = 2.0
ROI_COLOR_DEFAULT = 'r'
ROI_COLOR_HIGHLIGHT = 'g'


class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = plt.Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        self.roi_patches = []
        self.roi_active = None
        super(MplCanvas, self).__init__(self.fig)

    def imshow(self, np_array):
        self.axes.imshow(np_array)

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
        self.draw()

    def replace_roi(self, index, roi, color=ROI_COLOR_DEFAULT, zorder=PATCH_ZORDER_DEFAULT):
        patch = self._patch_from_roi(roi, color, zorder)
        self.roi_patches[index] = patch
        self.redraw_rois()

    def redraw_rois(self):
        self.axes.patches.clear()
        for patch in self.roi_patches:
            self.axes.add_patch(patch)
        self.draw()

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


def roi_from_row(row):
    if row[1] == 'Square':
        return SquareROI(row[4], row[2], row[3])
    elif row[1] == 'Circle':
        return CircleROI(row[4] / 2.0, row[2], row[3])
    raise ValueError


def mouse_is_over_selected_roi(event, row):
    return -row[4] / 2.0 < event.xdata - row[2] < + row[4] / 2.0 and -row[4] / 2.0 < event.ydata - row[3] < row[4] / 2.0


class RoiCreator(QMainWindow):
    def __init__(self):
        super(RoiCreator, self).__init__()

        self.canvas = MplCanvas()
        self.roimodel = ROITableModel()
        self.roitable = QTableView()
        self.roitable.setModel(self.roimodel)

        self.drag_callback_id = None
        self.drag_start_xy = None
        self.drag_roi_cxcy = None

        self.setGeometry(50, 50, 1200, 800)
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

    def roi_mouse_stop_drag(self, event):
        self.canvas.mpl_disconnect(self.drag_callback_id)

    def roi_mouse_start_drag(self, event):
        roi_index = self.roi_current_index()
        if roi_index is None:
            return
        row = self.roimodel.getRowData(roi_index)
        if mouse_is_over_selected_roi(event, row):
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
        row = self.roimodel.getRowData(roi_index)
        if mouse_is_over_selected_roi(event, row):
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
        lay_h_main.addWidget(self.canvas, 67)
        self.canvas.imshow(np.ones((200, 200)))
        # self.canvas.mpl_connect('motion_notify_event', self.react)
        self.canvas.mpl_connect('button_press_event', self.roi_mouse_start_drag)
        self.canvas.mpl_connect('scroll_event', self.roi_mouse_resize)

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

    def roi_redraw_all(self):
        print('Display ROIs')
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
