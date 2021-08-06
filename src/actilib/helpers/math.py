import numpy as np


def cart2pol(x, y):
    return np.arctan2(y, x), np.sqrt(x**2 + y**2)


