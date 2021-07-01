from pathlib import Path


def get_matlab_script_path():
    return str(Path(__file__).parent.parent / 'resources' / 'matlab')
