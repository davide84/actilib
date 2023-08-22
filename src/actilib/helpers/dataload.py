import json
import pkgutil
import tarfile
from pathlib import Path
from pydicom import dcmread
from pydicom.pixel_data_handlers import apply_rescale
from pydicom.pixel_data_handlers.util import apply_windowing


def load_test_data():
    return json.loads(pkgutil.get_data('actilib', str(Path('resources') / 'test_data.json')).decode("utf-8"))


def load_image_from_file(input_file):
    # image = {'header': None, 'pixels': None, 'window': None, 'source': 'path/to/file'}
    dicom_data = dcmread(input_file)
    image = {
        'pixels': apply_rescale(dicom_data.pixel_array, dicom_data),  # to have proper HU values
        'source': input_file.name
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
            images.append(load_image_from_file(file_dcm))
    return images


def load_images_from_directory(dir_path):
    images = []
    for file_path in sorted(Path(dir_path).glob('*')):
        if file_path.is_file():
            with open(file_path, 'rb+') as f:
                images.append(load_image_from_file(f))
    return images

