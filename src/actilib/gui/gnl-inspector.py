
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QSlider, QStatusBar, QHBoxLayout, QVBoxLayout,
                             QDesktopWidget, QPushButton, QFileDialog, QHeaderView, QTableView, QStyle, QGroupBox,
                             QLabel, QSpinBox, QComboBox, QSlider, QCheckBox, QGridLayout)
from PyQt5.QtCore import Qt

from actilib.gui.MplCanvas import MplCanvas

from actilib.analysis.segmentation import *
from actilib.analysis.gnl import calculate_gnl


BASE_TITLE = 'Actilib GNL Inspector'

WINDOWS_PARAMS = {
    'default': {'W': 800, 'C': -200},
    'Brain': {'W': 80, 'C': 40},
    'Bones': {'W': 1800, 'C': 400},
    'Lungs': {'W': 1500, 'C': -600},
    'Mediastinum': {'W': 350, 'C': 50},
    'Soft tissues': {'W': 400, 'C': 50},
    # 'Custom': {'W': 800, 'C': -200},  TODO implement later manual selection
}

ALPHA_SLIDER_STEP = 5
ALPHA_SLIDER_MAX = int(100/ALPHA_SLIDER_STEP)


class GNLInspector(QMainWindow):
    def __init__(self):
        super(GNLInspector, self).__init__()

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        self.lastPath = ''

        self.canvas = MplCanvas(hide_ticks=True)
        self.canvas.cursor_on_image.connect(self.update_cursor_position)
        self.canvas.scroll_event.connect(self.handle_scroll_event)

        # Cursor position and statistics
        self.lbl_pos_slice = QLabel('-/-')
        self.lbl_pos_mouse = QLabel('(-,-)')
        self.lbl_cur_huval = QLabel('n/a')

        # GNL parameters
        self.qcb_tissue = QComboBox()
        self.spb_hu_min = QSpinBox()
        self.spb_hu_max = QSpinBox()
        self.spb_hu_min.setRange(HUMIN, HUMAX)
        self.spb_hu_max.setRange(HUMIN, HUMAX)
        self.spb_hu_min.setValue(HUMIN)
        self.spb_hu_max.setValue(HUMAX)
        self.hu_custom_min = None
        self.hu_custom_max = None

        self.drag_callback_id = None
        self.drag_start_xy = None
        self.drag_roi_cxcy = None

        # display
        self.qcb_window = QComboBox()
        self.overlay_segmaps = [None]
        self.overlay_gnlmaps = [None]
        self.sli_alpha_img = QSlider(Qt.Horizontal)
        self.sli_alpha_seg = QSlider(Qt.Horizontal)
        self.sli_alpha_gnl = QSlider(Qt.Horizontal)
        for sli, value in [(self.sli_alpha_img, ALPHA_SLIDER_MAX), (self.sli_alpha_seg, 0),
                           (self.sli_alpha_gnl, int(75/ALPHA_SLIDER_STEP))]:
            sli.setRange(0, ALPHA_SLIDER_MAX)
            sli.setValue(value)
        self.lbl_curr_alpha_img = QLabel()
        self.lbl_curr_alpha_seg = QLabel()
        self.lbl_curr_alpha_gnl = QLabel()
        self.lbl_curr_alpha_img.setMinimumSize(50, 0)
        self.lbl_curr_alpha_img.setAlignment(Qt.AlignRight)
        self.update_alpha_labels()

        self.setGeometry(50, 50, 1300, 800)
        self.setWindowTitle(BASE_TITLE)
        #self.setWindowIcon(QIcon(resource_filename('isi.resources', 'templogo.jpg')))
        self.draw_ui()
        self.center()
        self.show()

    def center(self):
        qr = self.frameGeometry()  # geometry of the main window
        cp = QDesktopWidget().availableGeometry().center()  # center point of screen
        qr.moveCenter(cp)  # move rectangle's center point to screen's center point
        self.move(qr.topLeft())  # top left of rectangle becomes top left of window centering it

    def draw_ui(self):
        lay_h_main = QHBoxLayout()
        central_widget = QWidget()
        central_widget.setLayout(lay_h_main)
        self.setCentralWidget(central_widget)
        #
        # left panel: image display
        #
        lay_h_images = QHBoxLayout()
        # canvas
        self.canvas.image_loaded.connect(self.update_number_of_images)
        lay_h_images.addWidget(self.canvas)
        lay_h_main.addLayout(lay_h_images, 67)
        self.canvas.setAcceptDrops(True)
        # slider
        self.slider = QSlider(Qt.Vertical)
        self.slider.setMinimum(1)
        self.slider.setMaximum(1)
        self.slider.setTickPosition(QSlider.TicksRight)
        self.slider.setTickInterval(1)
        self.slider.valueChanged.connect(self.update_image)
        lay_h_images.addWidget(self.slider)
        #
        # right panel: GNL operations
        #
        lay_v_controls = QVBoxLayout()
        lay_h_main.addLayout(lay_v_controls, 33)
        #
        # Image Status Bar
        #
        gbx_cursor = QGroupBox('Cursor properties')
        lay_h_cursor = QHBoxLayout()
        gbx_cursor.setLayout(lay_h_cursor)
        lay_v_controls.addWidget(gbx_cursor)
        lay_h_cursor.addWidget(QLabel('Slice #:'), Qt.AlignLeft)
        lay_h_cursor.addWidget(self.lbl_pos_slice, Qt.AlignRight)
        lay_h_cursor.addWidget(QLabel('Position:'), Qt.AlignLeft)
        lay_h_cursor.addWidget(self.lbl_pos_mouse, Qt.AlignRight)
        lay_h_cursor.addWidget(QLabel('HU value:'), Qt.AlignLeft)
        lay_h_cursor.addWidget(self.lbl_cur_huval, Qt.AlignRight)
        #
        # GNL CALCULATION
        #
        gbx_gnl_params = QGroupBox('GNL calculation')
        lay_v_gnl = QVBoxLayout()
        gbx_gnl_params.setLayout(lay_v_gnl)
        lay_v_controls.addWidget(gbx_gnl_params)
        # GNL parameters filter
        lay_h_gnlpar = QHBoxLayout()
        lay_h_gnlpar.addWidget(QLabel('Tissue:'), alignment=Qt.AlignRight)
        for material, name in MAT_NAMES.items():
            self.qcb_tissue.addItem(name, material.value)
        self.qcb_tissue.currentTextChanged.connect(self.update_tissue)
        self.qcb_tissue.setCurrentText(MAT_NAMES[SegMats.SOFT_TISSUE])
        lay_h_gnlpar.addWidget(self.qcb_tissue)
        lay_h_gnlpar.addWidget(QLabel('HU interval:'), alignment=Qt.AlignRight)
        lay_h_gnlpar.addWidget(self.spb_hu_min)
        lay_h_gnlpar.addWidget(QLabel('to'), alignment=Qt.AlignCenter)
        lay_h_gnlpar.addWidget(self.spb_hu_max)
        self.spb_hu_min.editingFinished.connect(self.update_hu_ranges)
        self.spb_hu_max.editingFinished.connect(self.update_hu_ranges)
        lay_v_gnl.addLayout(lay_h_gnlpar)
        # GNL commands
        lay_h_gnlcmd = QHBoxLayout()
        btn_gnl_calc = QPushButton(' Calculate GNL')
        btn_gnl_calc.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_MediaPlay')))
        btn_gnl_calc.clicked.connect(self.calculate_gnl)
        lay_h_gnlcmd.addWidget(btn_gnl_calc)
        cbx_gnl_autocalc = QCheckBox(text='automatic recalculation')
        cbx_gnl_autocalc.setEnabled(False)
        lay_h_gnlcmd.addWidget(cbx_gnl_autocalc)
        lay_v_gnl.addLayout(lay_h_gnlcmd)
        #
        # VISUALIZATION SETTINGS
        #
        gbx_img_params = QGroupBox('Display settings')
        lay_g_alphas = QGridLayout()
        gbx_img_params.setLayout(lay_g_alphas)
        lay_v_controls.addWidget(gbx_img_params)
        # image windowing
        for window in WINDOWS_PARAMS:
            self.qcb_window.addItem(window)
        self.qcb_window.currentTextChanged.connect(self.update_image)
        lay_g_alphas.addWidget(QLabel('Display window:'), lay_g_alphas.rowCount(), 1, 1, 1)
        lay_g_alphas.addWidget(self.qcb_window, lay_g_alphas.rowCount() - 1, 2, 1, 1)
        # alpha values of overlays
        lay_g_alphas.addWidget(QLabel('Opacity of original image:'), lay_g_alphas.rowCount(), 1, 1, 1)
        lay_g_alphas.addWidget(self.sli_alpha_img, lay_g_alphas.rowCount() - 1, 2, 1, 1)
        lay_g_alphas.addWidget(self.lbl_curr_alpha_img, lay_g_alphas.rowCount() - 1, 3, 1, 1, Qt.AlignRight)
        lay_g_alphas.addWidget(QLabel('Opacity of segmentation:'), lay_g_alphas.rowCount(), 1, 1, 1)
        lay_g_alphas.addWidget(self.sli_alpha_seg, lay_g_alphas.rowCount() - 1, 2, 1, 1)
        lay_g_alphas.addWidget(self.lbl_curr_alpha_seg, lay_g_alphas.rowCount() - 1, 3, 1, 1, Qt.AlignRight)
        lay_g_alphas.addWidget(QLabel('Opacity of GNL maps:'), lay_g_alphas.rowCount(), 1, 1, 1)
        lay_g_alphas.addWidget(self.sli_alpha_gnl, lay_g_alphas.rowCount() - 1, 2, 1, 1)
        lay_g_alphas.addWidget(self.lbl_curr_alpha_gnl, lay_g_alphas.rowCount() - 1, 3, 1, 1, Qt.AlignRight)
        self.sli_alpha_img.valueChanged.connect(self.update_image)
        self.sli_alpha_seg.valueChanged.connect(self.update_image)
        self.sli_alpha_gnl.valueChanged.connect(self.update_image)
        #
        # FILLER
        #
        lay_v_controls.addStretch()

    def update_tissue(self, name):
        if name != MAT_NAMES[SegMats.CUSTOM]:
            hu_range = HU_RANGES_BY_NAME[name]
            self.spb_hu_min.setValue(hu_range[0])
            self.spb_hu_max.setValue(hu_range[1])
        else:
            if self.hu_custom_min is not None:
                self.spb_hu_min.setValue(self.hu_custom_min)
            if self.hu_custom_max is not None:
                self.spb_hu_max.setValue(self.hu_custom_max)
        # disabling editing for library materials
        self.spb_hu_min.setEnabled(name == MAT_NAMES[SegMats.CUSTOM])
        self.spb_hu_max.setEnabled(name == MAT_NAMES[SegMats.CUSTOM])

    def update_hu_ranges(self):
        self.spb_hu_min.setMaximum(self.spb_hu_max.value())
        self.spb_hu_max.setMinimum(self.spb_hu_min.value())
        # saving custom values
        if MAT_NAMES[SegMats.CUSTOM] == self.qcb_tissue.currentText():
            self.hu_custom_min = self.spb_hu_min.value()
            self.hu_custom_max = self.spb_hu_max.value()

    def calculate_gnl(self):
        image = self.canvas.get_current_image()
        if image is None:
            return
        self.statusBar.showMessage('Calculating GNL, this may take a few seconds...')
        tissue = SegMats(self.qcb_tissue.currentData())
        gnl, std, pixels, segmap, gnlmap = calculate_gnl(dicom_images=image,
                                                         tissues=tissue,
                                                         hu_ranges={tissue: [self.spb_hu_min.value(),
                                                                             self.spb_hu_max.value()]},
                                                         return_plot_data=True)
        self.overlay_segmaps[self.slider.value() - 1] = segmap
        self.overlay_gnlmaps[self.slider.value() - 1] = gnlmap
        self.update_image()
        self.statusBar.showMessage(u'GLN: {} \u00B1 {:.1f}'.format(gnl, std))

    def display_new_image_index(self):
        self.lbl_pos_slice.setText('{}/{}'.format(self.slider.value(), len(self.canvas.image_paths)))
        # self.statusBar.showMessage('Slice {} of {} - {}'.format(self.slider.value(), len(self.canvas.image_paths),
        #                            self.canvas.image_paths[self.slider.value()-1]), 3000)

    def update_number_of_images(self, img_num):
        self.overlay_segmaps = [None] * img_num
        self.overlay_gnlmaps = [None] * img_num
        self.slider.setMaximum(img_num)
        self.slider.setValue(int(img_num/2))
        self.slider.setTickPosition(QSlider.TicksRight)
        self.slider.setTickInterval(10)
        self.display_new_image_index()

    def update_alpha_labels(self):
        self.lbl_curr_alpha_img.setText('{} %'.format(ALPHA_SLIDER_STEP * self.sli_alpha_img.value()))
        self.lbl_curr_alpha_seg.setText('{} %'.format(ALPHA_SLIDER_STEP * self.sli_alpha_seg.value()))
        self.lbl_curr_alpha_gnl.setText('{} %'.format(ALPHA_SLIDER_STEP * self.sli_alpha_gnl.value()))

    def handle_scroll_event(self, direction):
        if 'down' == direction:
            self.slider.setValue(int(self.slider.value() - 1))
        elif 'up' == direction:
            self.slider.setValue(int(self.slider.value() + 1))

    def update_image(self):
        self.update_alpha_labels()
        hu_window = WINDOWS_PARAMS[self.qcb_window.currentText()]
        image_index = self.canvas.show_image(array_index=self.slider.value()-1, hu_window=hu_window,
                                             alpha=self.sli_alpha_img.value()/ALPHA_SLIDER_MAX)
        if image_index is not None:
            self.display_new_image_index()
            if self.overlay_segmaps[image_index] is not None:
                self.canvas.show_overlay(self.overlay_segmaps[image_index], alpha=self.sli_alpha_seg.value()/ALPHA_SLIDER_MAX)
            if self.overlay_gnlmaps[image_index] is not None:
                img = self.canvas.show_overlay(self.overlay_gnlmaps[image_index], alpha=self.sli_alpha_gnl.value()/ALPHA_SLIDER_MAX,
                                               cmap='nipy_spectral')
                self.canvas.show_colorbar(img)

    def update_cursor_position(self, x, y, hu):
        self.lbl_pos_mouse.setText('({},{})'.format(x, y))
        self.lbl_cur_huval.setText('{}'.format(hu))


if __name__ == '__main__':
    app = QApplication([])
    roi_creator = GNLInspector()
    app.exec_()
