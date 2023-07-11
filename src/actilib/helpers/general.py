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


def load_image_from_file(input_file):
    dicom_data = dcmread(input_file)
    image = {
        'pixels': apply_rescale(dicom_data.pixel_array, dicom_data)  # to have proper HU values
    }
    image['window'] = apply_windowing(image['pixels'], dicom_data)  # standard contrast for analysis
    input_file.seek(0)
    image['header'] = dcmread(input_file, stop_before_pixels=True)
    return image


def load_images_from_tar(tarpath):
    images = []
    with tarfile.open(tarpath, encoding='utf-8') as file_tar:
        for file_name in file_tar.getmembers():
            file_dcm = file_tar.extractfile(file_name)
            images.append(load_image_from_file(file_dcm))  # image = {'header': None, 'pixels': None, 'window': None}
    return images


def load_images_from_directory(dir_path):
    images = []
    with os.scandir(dir_path) as it:
        for entry in it:
            if entry.is_file():
                with open(entry.path, 'rb+') as f:
                    images.append(load_image_from_file(f))
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
