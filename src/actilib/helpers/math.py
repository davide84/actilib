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


def fft_frequencies(n_samples, pixel_size):
    sampling_rate = 1 / pixel_size
    frequency_spacing = sampling_rate / n_samples
    frequencies = [frequency_spacing * ns for ns in range(n_samples)]
    frequencies_shifted = np.fft.fftshift(frequencies)
    dc_index = np.where(frequencies_shifted == 0)[0][0]
    frequencies = [f - frequencies[dc_index] for f in frequencies]
    return frequencies


def running_mean(x, n=5):
    return np.convolve(x, np.ones((n,))/n)[(n-1):]


def smooth(x, window_size=5):
    # x: NumPy 1-D array containing the data to be smoothed
    # window_size: smoothing window size, must be odd number
    out0 = np.convolve(x, np.ones(window_size, dtype=int), 'valid') / window_size
    r = np.arange(1, window_size-1, 2)
    start = np.cumsum(x[:window_size-1])[::2]/r
    stop = (np.cumsum(x[:-window_size:-1])[::2]/r)[::-1]
    return np.concatenate((start, out0, stop))


def radial_profile(data_matrix, coord_x, coord_y=None):
    if coord_y is None:
        coord_y = coord_x
    data_size = data_matrix.shape[0]  # assume a square data_matrix
    mesh_x, mesh_y = np.meshgrid(coord_x, coord_y)
    _, mesh_r = cart2pol(mesh_x, mesh_y)
    r_values = np.linspace(0, np.ceil(2*np.abs(mesh_r[0, 0])), data_size)
    bin_matrix = np.digitize(mesh_r, r_values)
    p_values, v_values = np.zeros(r_values.shape), np.zeros(r_values.shape)
    for b in range(r_values.size):
        bin_contributors = data_matrix[bin_matrix == b]
        if len(bin_contributors) > 0:
            p_values[b] = np.mean(bin_contributors)
            v_values[b] = np.var(bin_contributors)
        else:
            p_values[b] = None
            v_values[b] = None
    # interpolate bins with 'None' with values from neighbors
    nans = np.isnan(p_values)
    p_values[nans] = np.interp(r_values[nans], r_values[~nans], p_values[~nans], left=0.0, right=0.0)
    v_values[nans] = np.interp(r_values[nans], r_values[~nans], v_values[~nans], left=0.0, right=0.0)
    return r_values, p_values, v_values
