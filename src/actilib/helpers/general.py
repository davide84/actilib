import json
import numpy as np
import os.path
import pkgutil
import tarfile
from pydicom import dcmread
from pydicom.pixel_data_handlers import apply_rescale
from pydicom.pixel_data_handlers.util import apply_windowing


def load_test_data():
    return json.loads(pkgutil.get_data('actilib', os.path.join('resources', 'test_data.json')).decode("utf-8"))


def load_images_from_tar(tarpath):
    images = []
    with tarfile.open(tarpath, encoding='utf-8') as file_tar:
        for file_name in file_tar.getmembers():
            images.append({'header': None, 'pixels': None, 'window': None})
            file_dcm = file_tar.extractfile(file_name)
            dicom_data = dcmread(file_dcm)
            images[-1]['pixels'] = apply_rescale(dicom_data.pixel_array, dicom_data)  # to have proper HU values
            images[-1]['window'] = apply_windowing(images[-1]['pixels'], dicom_data)  # standard contrast for analysis
            file_dcm.seek(0)
            images[-1]['header'] = dcmread(file_dcm, stop_before_pixels=True)
    return images


class ListBuffer:
    """
    Store lists of values and returns element-wise statistical properties.

    Useful to average data series and plot them with error bars.
    """

    def __init__(self):
        self.vectors = None

    def add_value_list(self, values_list):
        if self.vectors is None:
            self.vectors = np.array(values_list)
        else:
            self.vectors = np.vstack((self.vectors, values_list))

    def mean(self):
        return np.mean(self.vectors, axis=0)

    def std(self):
        return np.std(self.vectors, axis=0)

    def se(self):
        return np.std(self.vectors, axis=0) / np.sqrt(len(self.vectors))
