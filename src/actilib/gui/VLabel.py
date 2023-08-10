from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QPainter
from PyQt5.QtCore import Qt, QSize


class VLabel(QLabel):
    def __init__(self, *args):
        QLabel.__init__(self, *args)
        QLabel.show(self)  # needed so the QLabel can calculate its width, used just below
        self.setFixedSize(QLabel.size(self).width(), QLabel.size(self).height())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(Qt.black)
        painter.translate(15, self.size().height()-1)
        painter.rotate(-90)
        painter.drawText(0, 0, QLabel.text(self))
        painter.end()

    def minimumSizeHint(self):
        size = QLabel.minimumSizeHint(self)
        return QSize(size.height(), size.width())

    def sizeHint(self):
        size = QLabel.sizeHint(self)
        return QSize(size.height(), size.width())