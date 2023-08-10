from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QTabWidget, QMenuBar, QDialog,
                             QGridLayout, QVBoxLayout, QGroupBox, QDateEdit, QTimeEdit, QDesktopWidget,
                             QPushButton, QLabel, QTableView, QLineEdit, QPlainTextEdit, QFileDialog, QHeaderView,
                             QCheckBox)
from PyQt5.QtCore import QDate, QTime
from pathlib import Path
from tempfile import TemporaryDirectory
import csv
import json
import gettext
from uszcert.functions import format_date, prepare_pdf, send_email
from actilib.gui.TableModel import TableModel


MAX_SPEAKERS = 3
MAX_TOPICS = 5
MAX_SIGNATURES = 3


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.lang = 'en'
        self._ = gettext.gettext
        self.menubar = QMenuBar()
        self.values = {'version': uszcert.__version__}
        self.qobj = {}
        self.chb_email_cc = None
        self.table = QTableView()
        self.table_model = None

        self.setGeometry(50, 50, 600, 800)
        self.setWindowTitle("USZCert")
        #self.setWindowIcon(QIcon(resource_filename('isi.resources', 'templogo.jpg')))

        self.draw_ui()
        self.read_template_from_file('default.uct')
        self.center()
        self.show()

    def draw_ui(self):
        field_names = {
            'header_line_1': self._('Header, 1st line'),
            'header_line_2': self._('Header, 2nd line'),
            'title': self._('Event title'),
            'place': self._('Location'),
            'date': self._('Date'),
            'time_from': self._('From'),
            'time_to': self._('To'),
            'speakers': [self._('Speakers'), self._('Name'), self._('Affiliation')],
            'topics': self._('Topics'),
            'credits': self._('Credits'),
            'signatures': [self._('Signatures'), self._('Name'), self._('Title'), self._('Image file')],
            'sender': self._('Sender'),
            'subject': self._('Subject'),
            'email_body': self._('Email body')
        }

        #
        # Menu
        #
        self.menubar = QMenuBar()
        # File menu
        menu_file = self.menubar.addMenu(self._('&File'))
        menu_template = menu_file.addMenu(self._('&Templates'))
        menu_action_load = menu_template.addAction(self._('&Load template...'))
        menu_action_load.triggered.connect(self.load_template_dialog)
        menu_action_save = menu_template.addAction(self._('&Save template...'))
        menu_action_save.triggered.connect(self.save_template_dialog)
        menu_attendees = menu_file.addMenu(self._('&Attendees'))
        menu_action_load = menu_attendees.addAction(self._('&Import attendee list...'))
        menu_action_load.triggered.connect(self.import_attendees_dialog)
        menu_action_save = menu_attendees.addAction(self._('&Export attendee list...'))
        menu_action_save.triggered.connect(self.export_attendees_dialog)
        menu_action_exit = menu_file.addAction(self._('&Exit'))
        menu_action_exit.triggered.connect(QApplication.quit)
        # Options menu
        menu_options = self.menubar.addMenu(self._('&Options'))
        menu_lang = menu_options.addMenu(self._('&Languages'))
        menu_lang_de = menu_lang.addAction('&Deutsch')
        menu_lang_de.triggered.connect(lambda: self.switch_language("de"))
        menu_lang_en = menu_lang.addAction('&English')
        menu_lang_en.triggered.connect(lambda: self.switch_language("en"))
        # Help menu
        menu_help = self.menubar.addMenu(self._('&Help'))
        menu_help_about = menu_help.addAction(self._('&About...'))
        menu_help_about.triggered.connect(self.show_credits)
        self.setMenuBar(self.menubar)

        #
        # Main Tab Widget
        #
        self.tab_widget = QTabWidget(self)
        self.tab_ids = {}
        self.setCentralWidget(self.tab_widget)

        #
        # 'Content' tab
        #
        tab_content = QWidget()
        lay_content = QGridLayout()
        tab_content.setLayout(lay_content)
        self.tab_ids['content'] = self.tab_widget.addTab(tab_content, self._('Content'))

        lay_content.setColumnStretch(1, 10)
        lay_content.setColumnStretch(3, 10)
        lay_content.setColumnStretch(5, 10)
        lay_content.setColumnStretch(6, 1)
        lay_content.setColumnStretch(7, 10)

        def add_qle(layout, name, label):
            layout.addWidget(QLabel(label), layout.rowCount(), 0)
            self.qobj[name] = QLineEdit()
            self.qobj[name].editingFinished.connect(lambda b=name: self.values.update({b: self.qobj[b].text()}))
            layout.addWidget(self.qobj[name], layout.rowCount() - 1, 1, 1, -1)

        def add_qpe(layout, name, label):
            layout.addWidget(QLabel(label), layout.rowCount(), 0)
            self.qobj[name] = QPlainTextEdit()
            self.qobj[name].textChanged.connect(lambda b=name: self.values.update({b: self.qobj[b].toPlainText()}))
            layout.addWidget(self.qobj[name], layout.rowCount() - 1, 1, 1, -1)

        for k in ['header_line_1', 'header_line_2', 'title', 'place']:
            add_qle(lay_content, k, field_names[k])

        def highlight_second_calendar():
            if self.qobj['date_end'].date() > self.qobj['date'].date():
                self.qobj['date_end'].setStyleSheet("")
            else:
                self.qobj['date_end'].setStyleSheet("QDateEdit {background: lightgray;}")

        lay_content.addWidget(QLabel(self._('Date')), lay_content.rowCount(), 0)
        self.qobj['date'] = QDateEdit()
        self.qobj['date'].setCalendarPopup(True)
        self.qobj['date'].editingFinished.connect(lambda: self.values.update({"date": self.qobj['date'].date().toString("dd.MM.yyyy")}))
        lay_content.addWidget(self.qobj['date'], lay_content.rowCount() - 1, 1)
        lay_content.addWidget(QLabel('-'), lay_content.rowCount() - 1, 2)
        self.qobj['date_end'] = QDateEdit()
        self.qobj['date_end'].setCalendarPopup(True)
        self.qobj['date_end'].setStyleSheet("QDateEdit {background: lightgray;}")
        self.qobj['date_end'].editingFinished.connect(lambda: self.values.update({"date_end": self.qobj['date_end'].date().toString("dd.MM.yyyy")}))
        self.qobj['date_end'].editingFinished.connect(highlight_second_calendar)
        lay_content.addWidget(self.qobj['date_end'], lay_content.rowCount() - 1, 3)

        for k, key in enumerate(['time_from', 'time_to']):
            time_label = self._('From') if key == 'time_from' else self._('To')
            lay_content.addWidget(QLabel(time_label.lower()), lay_content.rowCount() - 1, 4 + 2 * k)
            self.qobj[key] = QTimeEdit()
            self.qobj[key].editingFinished.connect(lambda b=key: self.values.update({b: self.qobj[b].time().toString("hh:mm")}))
            lay_content.addWidget(self.qobj[key], lay_content.rowCount() - 1, 5 + 2 * k)

        add_qle(lay_content, 'credits', field_names['credits'])

        # group - speakers

        groupbox_speakers = QGroupBox(field_names['speakers'][0])
        lay_content.addWidget(groupbox_speakers, lay_content.rowCount(), 0, 1, lay_content.columnCount())
        lay_speakers = QGridLayout()
        groupbox_speakers.setLayout(lay_speakers)

        self.qobj['speakers'] = []

        nspan = 2
        aspan = lay_content.columnCount() - nspan

        def add_speaker(layout):
            ns = len(self.qobj['speakers'])
            self.qobj['speakers'].append([])
            speaker = self.qobj['speakers'][-1]
            for j in range(2):
                speaker.append(QLineEdit())
                speaker[-1].editingFinished.connect(lambda: self.update_fields('speakers'))
                layout.addWidget(speaker[-1], layout.rowCount() - j, 2 * j, 1, nspan if j == 0 else aspan)

        lay_speakers.addWidget(QLabel(field_names['speakers'][1]), lay_speakers.rowCount(), 0, 1, nspan)
        lay_speakers.addWidget(QLabel(field_names['speakers'][2]), lay_speakers.rowCount() - 1, 2, 1, aspan)
        for i in range(3):
            add_speaker(lay_speakers)

        # group - topics

        groupbox_topics = QGroupBox(field_names['topics'])
        lay_content.addWidget(groupbox_topics, lay_content.rowCount(), 0, 1, lay_content.columnCount())
        lay_topics = QVBoxLayout()
        groupbox_topics.setLayout(lay_topics)
        self.qobj['topics'] = []

        def add_qle_topic(layout):
            self.qobj['topics'].append(QLineEdit())
            self.qobj['topics'][-1].editingFinished.connect(lambda: self.update_fields('topics'))
            layout.addWidget(self.qobj['topics'][-1])

        for i in range(MAX_TOPICS):
            add_qle_topic(lay_topics)

        # group - signatures

        groupbox_signatures = QGroupBox(field_names['signatures'][0])
        lay_content.addWidget(groupbox_signatures, lay_content.rowCount(), 0, 1, lay_content.columnCount())
        lay_signatures = QGridLayout()
        groupbox_signatures.setLayout(lay_signatures)

        self.qobj['signatures'] = []

        def select_signature(index):
            sign_path = Path(self.values['signatures'][index][2])
            fname = QFileDialog.getOpenFileName(self, 'Open file', str(sign_path.parent.absolute()),
                                                "Image files (*.jpg *.jpeg *.gif *.png)")
            sign_path = Path(fname[0] if isinstance(fname, tuple) else fname)
            self.qobj['signatures'][index][2].setText(sign_path.name)
            self.values['signatures'][index][2] = str(sign_path)

        def add_signature(layout):
            ns = len(self.qobj['signatures'])
            self.qobj['signatures'].append([])
            signature = self.qobj['signatures'][-1]
            for j in range(3):
                signature.append(QLineEdit())
                signature[-1].editingFinished.connect(lambda: self.update_fields('signatures'))
                layout.addWidget(signature[-1], layout.rowCount() - min(j, 1), j)
            # adding the file selection for the third field
            signature[-1].setReadOnly(True)
            pbtn = QPushButton('...')
            pbtn.setFixedWidth(25)
            pbtn.clicked.connect(lambda: select_signature(ns))
            layout.addWidget(pbtn, layout.rowCount() - 1, 4)

        for i in range(3):
            lay_signatures.addWidget(QLabel(field_names['signatures'][i + 1]), lay_signatures.rowCount() - min(1, i), i)

        for i in range(MAX_SIGNATURES):
            add_signature(lay_signatures)

        btn_preview = QPushButton(self._('Preview certificate'))
        btn_preview.clicked.connect(self.preview_pdf)
        lay_content.addWidget(btn_preview, lay_content.rowCount(), lay_content.columnCount() - 3, 1, 3)

        #
        # 'Attendees' tab
        #

        tab_people = QWidget()
        lay_people = QGridLayout()
        tab_people.setLayout(lay_people)
        self.tab_ids['people'] = self.tab_widget.addTab(tab_people, self._('Attendees'))

        table_header = [self._('First Name'), self._('Last Name'), self._('Birthdate'), self._('Email address')]
        table_data = [[''] * len(table_header)]
        self.table_model = TableModel(table_data, table_header)
        self.table.setModel(self.table_model)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay_people.addWidget(self.table)

        #
        # 'Email' tab
        #
        tab_email = QWidget()
        lay_email = QGridLayout()
        tab_email.setLayout(lay_email)

        self.tab_ids['email'] = self.tab_widget.addTab(tab_email, self._('Email'))
        add_qle(lay_email, 'sender', field_names['sender'])
        add_qle(lay_email, 'subject', field_names['subject'])
        add_qpe(lay_email, 'email_body', field_names['email_body'])
        self.chb_email_cc = QCheckBox(self._('Sender in CC'))
        self.chb_email_cc.setChecked(True)
        lay_email.addWidget(self.chb_email_cc, lay_email.rowCount(), 0)
        btn_test_mail = QPushButton(self._('Send a test email to sender'))
        btn_test_mail.clicked.connect(self.send_test_mail)
        lay_email.addWidget(btn_test_mail, lay_email.rowCount() - 1, 1)
        btn_send_cert = QPushButton(self._('Send certificates'))
        btn_send_cert.clicked.connect(self.send_certificates)
        lay_email.addWidget(btn_send_cert, lay_email.rowCount() - 1, 2)

    def center(self):
        # geometry of the main window
        qr = self.frameGeometry()
        # center point of screen
        cp = QDesktopWidget().availableGeometry().center()
        # move rectangle's center point to screen's center point
        qr.moveCenter(cp)
        # top left of rectangle becomes top left of window centering it
        self.move(qr.topLeft())

    def show_credits(self):
        lay_dialog = QVBoxLayout()
        lay_dialog.addWidget(QLabel('USZCert {}, {} Davide Cester (2023)'.format(uszcert.__version__, self._('written by'))))
        lay_dialog.addWidget(QLabel(self._('Institute for Diagnostic and Interventional Radiology (DIR)')))
        qdial = QDialog(self)
        qdial.setWindowTitle(self._('About...'))
        qdial.setLayout(lay_dialog)
        qdial.exec()

    def switch_language(self, lang):
        curr_tab_id = self.tab_widget.currentIndex()
        self.lang = lang
        temppath = Path(TemporaryDirectory(prefix='uszcert_').name)
        temppath.mkdir(parents=True, exist_ok=True)  # ensure directory exists
        self.write_template_to_file(temppath / 'current_values.uct')
        self.write_attendees_to_file(temppath / 'current_attendees.csv')
        language = gettext.translation('base', localedir='locales', languages=[self.lang])
        language.install()
        self._ = language.gettext
        self.draw_ui()
        self.read_template_from_file(temppath / 'current_values.uct')
        self.read_attendees_from_file(temppath / 'current_attendees.csv')
        self.tab_widget.setCurrentIndex(curr_tab_id)

    def load_template_dialog(self):
        fname = QFileDialog.getOpenFileName(self, 'Open file', '.', "Certificate templates *.uct (*.uct)")
        if fname != ('', ''):
            file_open = Path(fname[0] if isinstance(fname, tuple) else fname)
            self.read_template_from_file(file_open)

    def read_template_from_file(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as fin:
            self.values.update(json.load(fin))
            self.apply_values()

    def save_template_dialog(self):
        fname = QFileDialog.getSaveFileName(self, 'Save file', '.', "Certificate templates *.uct (*.uct)")
        if fname != ('', ''):
            file_path = Path(fname[0] if isinstance(fname, tuple) else fname).with_suffix('.uct')
            self.write_template_to_file(file_path)

    def write_template_to_file(self, file_path):
        with open(file_path, 'w', encoding='utf-8') as fout:
            json.dump(self.values, fout, indent=4)

    def apply_values(self):
        # QLineEdit items
        for key, obj in self.qobj.items():
            if key == 'version':  # nothing to be set in GUI
                continue
            if isinstance(obj, QLineEdit):
                self.qobj[key].setText(self.values[key])
            elif isinstance(obj, QPlainTextEdit):
                self.qobj[key].setPlainText(self.values[key])
            elif isinstance(obj, QDateEdit):
                date_elements = [int(x) for x in self.values[key].split('.')]
                self.qobj[key].setDate(QDate(date_elements[2], date_elements[1], date_elements[0]))
            elif isinstance(obj, QTimeEdit):
                time_elements = [int(x) for x in self.values[key].split(':')]
                self.qobj[key].setTime(QTime(time_elements[0], time_elements[1]))
            elif isinstance(obj, list):
                if isinstance(obj[0], list):  # nested list
                    for r in range(min(len(self.values[key]), len(self.qobj[key]))):
                        for c in range(min(len(self.values[key][0]), len(self.qobj[key][0]))):
                            # special cases
                            if key == 'signatures' and c == 2:
                                if self.values[key][r][c] is None:
                                    continue
                                path = Path(self.values[key][r][c])
                                if path.exists():
                                    obj[r][c].setText(Path(self.values[key][r][c]).name)
                                else:
                                    self.values[key][r][c] = None
                            else:
                                obj[r][c].setText(self.values[key][r][c])
                else:
                    for c in range(min(len(self.values[key]), len(self.qobj[key]))):
                        obj[c].setText(self.values[key][c])

    def update_fields(self, key):
        self.values[key] = []
        for s in self.qobj[key]:
            if isinstance(s, list):
                ret = []
                for f in s:
                    ret.append(f.text())
                if ret != len(ret) * ['']:
                    self.values[key].append(ret)
            else:
                self.values[key].append(s.text())

    def import_attendees_dialog(self):
        fname = QFileDialog.getOpenFileName(self, 'Open file', '.', "Comma Separated Files *.csv (*.csv)")
        if fname != ('', ''):
            file_path = Path(fname[0] if isinstance(fname, tuple) else fname).with_suffix('.csv')
            self.read_attendees_from_file(file_path)
            self.tab_widget.setCurrentIndex(self.tab_ids['people'])

    def read_attendees_from_file(self, file_path):
        data = []
        with open(file_path, 'r', encoding='utf-8') as fin:
            reader = csv.reader(fin, dialect='excel', lineterminator='\n')
            next(reader)  # skip header
            for row in reader:
                data.append(row)
        self.table_model = TableModel(data, self.table_model.getColumns())
        self.table.setModel(self.table_model)

    def export_attendees_dialog(self):
        fname = QFileDialog.getSaveFileName(self, 'Save file', '.', "Comma Separated Files *.csv (*.csv)")
        if fname != ('', ''):
            file_path = Path(fname[0] if isinstance(fname, tuple) else fname).with_suffix('.csv')
            self.write_attendees_to_file(file_path)

    def write_attendees_to_file(self, file_path):
        with open(file_path, 'w', encoding='utf-8') as fout:
            writer = csv.writer(fout, dialect='excel', lineterminator='\n')
            writer.writerow(self.table_model.getColumns())
            for r in range(self.table_model.rowCount(0)):
                writer.writerow(self.table_model.getRowData(r))

    def closeEvent(self, event):
        return
        # with open(self.file_pref_global, 'w') as f:
        #     json.dump(self.config, f)

    def preview_pdf(self):
        pdf_path = prepare_pdf('Thomas', 'Mustermann', '19.02.1984', self.values, self.lang)
        import subprocess, os, platform
        if platform.system() == 'Darwin':  # macOS
            subprocess.call(('open', pdf_path))
        elif platform.system() == 'Windows':  # Windows
            os.startfile(pdf_path)
        else:  # linux variants
            subprocess.call(('xdg-open', pdf_path))
        return pdf_path

    def parsed_body(self):
        # date is already in format 'dd.MM.yyyy' in self.values
        return self.values['email_body'].replace('%DATE%', format_date(self.values, self.lang, self._))

    def send_test_mail(self):
        filepath = prepare_pdf('Thomas', 'Mustermann', '19.02.1984', self.values, self.lang)
        send_email(self.values['sender'], self.values['subject'], self.parsed_body(),
                   self.values['sender'], None, filepath)

    def send_certificates(self):
        for r in range(self.table_model.rowCount(0)):
            row = self.table_model.getRowData(r)
            # primitive validation
            for i in [0, 1, 3]:  # 2 = birthdate, we allow that to be empty
                if row[i] == '':
                    return
            filepath = prepare_pdf(row[0], row[1], row[2], self.values, self.lang)
            cc = self.values['sender'] if self.chb_email_cc.isChecked() else None
            send_email(self.values['sender'], self.values['subject'], self.parsed_body(), row[3], cc, filepath)
