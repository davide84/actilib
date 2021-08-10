import math
import numpy as np


def rad_from_deg(deg):
    return deg * 2 * math.pi / 360.0


def cart2pol(x, y):
    return np.arctan2(y, x), np.sqrt(x**2 + y**2)


def polyfit2d(x, y, z, order=2):
    """
    Parameters
    ----------
    x, y: meshgrids of X and Y coordinates, respectively.
    z: the data to be fitted. Must have the same size as x and y.
    order: the maximum order to be considered (including combinations of X and Y).
    """
    order = 1 + order
    a = np.zeros((order**2, x.size))
    for k, (j, i) in enumerate(np.ndindex((order, order))):
        if i + j > order:  # excluding higher combinations (e.g. X^2*Y, X*Y^2 and X^2*Y^2 for order=2)
            arr = np.zeros_like(x)
        else:
            arr = x**i * y**j
        a[k] = arr.ravel()
    return np.linalg.lstsq(a.T, np.ravel(z), rcond=None)


def subtract_2d_poly_mean(image):
    size_x, size_y = image.shape[1], image.shape[0]
    x = np.linspace(-size_x/2, size_x/2, size_x)
    y = np.linspace(-size_y/2, size_y/2, size_y)
    x, y = np.meshgrid(x, y)
    c = polyfit2d(x, y, image)[0]  # function returns more...
    return image - (c[2] * x**2 + c[5] * x * y + c[6] * y**2 + c[1] * x + c[3] * y + c[0])



