from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex


class TableModel(QAbstractTableModel):
    def __init__(self, columns=None, dummyrow=None):
        super().__init__()
        self._columns = ['Name', 'Shape', 'Center X', 'Center Y', 'Size'] if columns is None else columns
        self._dummyrow = ['', '', 0, 0, 0] if dummyrow is None else dummyrow
        self._data = [self._dummyrow.copy()]  # needed otherwise header won't show up

    def rowCount(self, index):
        # The length of the outer list.
        return len(self._data)

    def columnCount(self, index):
        # The following takes the first sub-list, and returns
        # the length (only works if all rows are an equal length)
        return len(self._data[0])

    def getColumns(self):
        return self._columns

    def getRowData(self, row_index):
        return self._data[row_index]

    def getRowTemplate(self):
        return self._dummyrow.copy()

    def getProgressiveRowCounter(self):
        return self._add_counter

    def clear(self):
        self._data = [self._dummyrow.copy()]
        self.layoutChanged.emit()

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole or role == Qt.EditRole:
                value = self._data[index.row()][index.column()]
                return str(value)

    def setData(self, index, value, role):
        if role == Qt.EditRole and value:
            if index.column() in [2, 3, 4]:
                try:
                    value = int(value)
                    if value < 0:
                        return False
                except ValueError:
                    return False
            self._data[index.row()][index.column()] = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def addRow(self, row_data, position='bottom'):
        if self._data[-1] == self._dummyrow:
            self._data[-1] = row_data
        else:
            if 'top' == position:
                self._data.insert(0, row_data)
            else:
                self._data.append(row_data)
        self.layoutChanged.emit()

    def removeRow(self, row: int, parent: QModelIndex = ...) -> bool:
        if self._data[row] != self._dummyrow:
            self._data.pop(row)
            self.layoutChanged.emit()
            return True
        return False

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        # for setting columns name
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._columns[section]
        elif orientation == Qt.Vertical and role == Qt.DisplayRole:
            return section

    def setHeaderData(self, section, orientation, data, role=Qt.EditRole):
        if orientation == Qt.Horizontal and role in (Qt.DisplayRole, Qt.EditRole):
            try:
                self.horizontalHeaders[section] = data
                return True
            except Exception as e:
                return False
        return super().setHeaderData(section, orientation, self._columns[section], role)

    def flags(self, index):
        if index.column() == 1 or self._data[-1] == self._dummyrow:  # Shape and initial row not editable
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable
