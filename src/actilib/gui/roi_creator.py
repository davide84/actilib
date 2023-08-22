import json

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QSlider, QStatusBar, QHBoxLayout, QVBoxLayout,
                             QDesktopWidget, QPushButton, QFileDialog, QHeaderView, QTableView, QStyle, QGroupBox,
                             QLabel, QSpinBox)
from pathlib import Path
from PyQt5.QtCore import Qt
from actilib.analysis.rois import CircleROI, SquareROI
from actilib.gui.TableModel import ROITableModel
from actilib.gui.MplCanvas import MplCanvas


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

        self.spb_slice_first = QSpinBox()
        self.spb_slice_last = QSpinBox()
        self.spb_slice_first.setMaximum(0)
        self.spb_slice_last.setMaximum(0)

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
        self.canvas.image_loaded.connect(self.update_number_of_images)
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
        btn_roi_loa = QPushButton(' Load...')
        btn_roi_loa.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_DialogOpenButton')))
        btn_roi_loa.clicked.connect(self.roi_load_list)
        lay_h_roibtns.addWidget(btn_roi_loa)
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
        btn_roi_sav = QPushButton(' Save...')
        btn_roi_sav.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_DialogSaveButton')))
        btn_roi_sav.clicked.connect(self.roi_save_list)
        lay_h_roibtns.addWidget(btn_roi_sav)
        lay_v_rois.addLayout(lay_h_roibtns)
        # ROI table
        self.roitable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.roitable.verticalHeader().setVisible(True)
        self.roitable.verticalHeader().setFixedWidth(20)
        self.roimodel.dataChanged.connect(self.roi_update_current)  # changed ROI
        self.roitable.clicked.connect(self.roi_highlight_selected)  # selected another ROI
        lay_v_rois.addWidget(self.roitable)
        # Slice filter
        gbx_image_filter = QGroupBox('Image range selection')
        lay_h_imgfil = QHBoxLayout()
        lay_h_imgfil.addWidget(QLabel('First slice:'), alignment=Qt.AlignRight)
        lay_h_imgfil.addWidget(self.spb_slice_first)
        lay_h_imgfil.addWidget(QLabel('Last slice:'), alignment=Qt.AlignRight)
        lay_h_imgfil.addWidget(self.spb_slice_last)
        self.spb_slice_first.valueChanged.connect(self.update_image_range_lower)
        self.spb_slice_last.valueChanged.connect(self.update_image_range_upper)
        gbx_image_filter.setLayout(lay_h_imgfil)
        lay_v_rois.addWidget(gbx_image_filter)

    def update_image_range_lower(self, new_limit):
        if new_limit > self.spb_slice_last.value():
            new_limit = self.spb_slice_last.value()
            self.spb_slice_first.setValue(new_limit)
        self.slider.setMinimum(new_limit)
        self.display_new_image_index()

    def update_image_range_upper(self, new_limit):
        if new_limit < self.spb_slice_first.value():
            new_limit = self.spb_slice_first.value()
            self.spb_slice_last.setValue(new_limit)
        self.slider.setMaximum(new_limit)
        self.display_new_image_index()

    def display_new_image_index(self):
        self.statusBar.showMessage('Slice {} of {} - {}'.format(self.slider.value(), len(self.canvas.image_paths),
                                   self.canvas.image_paths[self.slider.value()-1]))

    def update_number_of_images(self, img_num):
        # order of operations matter here: first set the maximum, then set the minimum
        # otherwise we may have for a moment min = 1 > max = 0 and the slider won't update its minimum properly
        self.spb_slice_first.setMaximum(img_num)
        self.spb_slice_last.setMaximum(img_num)
        self.spb_slice_last.setValue(img_num)
        self.spb_slice_first.setMinimum(1)
        self.spb_slice_last.setMinimum(1)
        self.spb_slice_first.setValue(1)
        self.display_new_image_index()

    def select_image(self):
        image_index = self.canvas.show_image(array_index=self.slider.value()-1)
        if image_index is not None:
            self.display_new_image_index()

    def roi_redraw_all(self):
        self.canvas.clear_rois()
        for r in range(self.roimodel.rowCount(0)):
            self.canvas.add_roi(roi_from_row(self.roimodel.getRowData(r)))
        self.roi_highlight_selected()

    def roi_remove_selected(self):
        try:
            if self.roimodel.removeRow(self.roi_current_index()):
                self.roi_redraw_all()
        except IndexError:
            pass

    def roi_update_current(self):
        roi_index = self.roi_current_index()
        new_roi = roi_from_row(self.roimodel.getRowData(roi_index))
        self.canvas.replace_roi(roi_index, new_roi)
        self.roi_highlight_selected()

    def roi_highlight_selected(self):
        if self.roi_current_index() is not None:
            self.canvas.highlight_roi(self.roi_current_index())

    def roi_add(self, shape):
        self.roimodel.addRow(shape)
        self.roitable.selectRow(self.roimodel.rowCount(0) - 1)
        self.canvas.add_roi(roi_from_row(self.roimodel.getRowData(self.roimodel.rowCount(0) - 1)))
        self.roi_highlight_selected()

    def roi_load_list(self):
        # select file and write
        fname = QFileDialog.getOpenFileName(self, 'Open file', '.', "JSON text file (*.json)")
        if fname != ('', ''):
            file_path = Path(fname[0] if isinstance(fname, tuple) else fname).with_suffix('.json')
            with open(file_path, 'r', encoding='utf-8') as fin:
                data = json.load(fin)
            # loading images first
            self.canvas.recursively_validate_and_load_files(data['images']['files'])
            self.spb_slice_last.setValue(data['images']['last'])
            self.spb_slice_first.setValue(data['images']['first'])
            self.slider.setValue(self.spb_slice_first.value())
            # loading ROIs
            self.roimodel.clear()
            header = self.roimodel.getColumns()
            for roi in data['rois']:
                self.roimodel.addRow(roi[header[1]], roi[header[2]], roi[header[3]], roi[header[4]], roi[header[0]])
            self.roitable.selectRow(0)
            self.roi_redraw_all()

    def roi_save_list(self):
        # prepare the data structure for writeout
        roi_out = []
        for r in range(self.roimodel.rowCount(0)):
            row = self.roimodel.getRowData(r)
            columns = self.roimodel.getColumns()
            roi_out.append({
                columns[0]: row[0],
                columns[1]: row[1],
                columns[2]: row[2],
                columns[3]: row[3],
                columns[4]: row[4]
            })
        imgs_out = {
            'files': self.canvas.image_paths,
            'first': self.spb_slice_first.value(),
            'last': self.spb_slice_last.value()
        }
        # select file and write
        fname = QFileDialog.getSaveFileName(self, 'Save file', '.', "JSON text file (*.json)")
        if fname != ('', ''):
            file_path = Path(fname[0] if isinstance(fname, tuple) else fname).with_suffix('.json')
            with open(file_path, 'w', encoding='utf-8') as fout:
                json.dump({'images': imgs_out, 'rois': roi_out}, fout, indent=4)


if __name__ == '__main__':
    app = QApplication([])
    roi_creator = RoiCreator()
    app.exec_()
