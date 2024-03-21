import json
import pkgutil
import tarfile
from pathlib import Path
from pydicom import dcmread
from pydicom.pixel_data_handlers import apply_rescale
from pydicom.pixel_data_handlers.util import apply_windowing


JSON_FLOAT_ROUNDING_FORMAT = '.2f'


class RoundingFloat(float):
    __repr__ = staticmethod(lambda x: format(x, JSON_FLOAT_ROUNDING_FORMAT))


def set_json_dump_float_precision(decimals):
    global JSON_FLOAT_ROUNDING_FORMAT
    if decimals in range(16):
        JSON_FLOAT_ROUNDING_FORMAT = '.{}f'.format(decimals)
        json.encoder.c_make_encoder = None
        if hasattr(json.encoder, 'FLOAT_REPR'):
            # Python 2
            json.encoder.FLOAT_REPR = RoundingFloat.__repr__
        else:
            # Python 3
            json.encoder.float = RoundingFloat


def reset_json_dump_float_precision():
    json.encoder.c_make_encoder = True


def load_test_data():
    return json.loads(pkgutil.get_data('actilib', str(Path('resources') / 'test_data.json')).decode("utf-8"))


def load_image_from_file(input_file):
    # image = {'header': None, 'pixels': None, 'source': 'path/to/file'}
    dicom_data = dcmread(input_file)
    image = {
        'pixels': apply_rescale(dicom_data.pixel_array, dicom_data),  # to have proper HU values
        'source': input_file.name
    }
    input_file.seek(0)
    image['header'] = dcmread(input_file, stop_before_pixels=True)
    return image


def load_images_from_tar(tar_path):
    images = []
    with tarfile.open(tar_path, encoding='utf-8') as file_tar:
        for file_name in file_tar.getmembers():
            file_dcm = file_tar.extractfile(file_name)
            images.append(load_image_from_file(file_dcm))
    return images


def load_images_from_directory(dir_path, sort_by_instance_number=True):
    images = []
    for file_path in sorted(Path(dir_path).glob('*')):
        if file_path.is_file():
            with open(file_path, 'rb+') as f:
                image = load_image_from_file(f)
                images.append((image['header'].InstanceNumber - 1, image))
    if sort_by_instance_number:
        images = sorted(images)
    return [couple[1] for couple in images]

