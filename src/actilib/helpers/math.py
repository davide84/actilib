import math
import cv2 as cv
import numpy as np


def deg_from_rad(rad):
    return rad * 360 / (2 * math.pi)


def rad_from_deg(deg):
    return deg * 2 * math.pi / 360.0


def cart2pol(x, y):
    # np.hypot(x, y) equivalent to np.sqrt(x**2 + y**2) but less (or no) risk of ever overflowing
    return np.arctan2(y, x), np.hypot(x, y)


def pol2cart(theta, rho):
    return rho * np.cos(theta), rho * np.sin(theta)


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


def fft_frequencies(num_samples, sampling_spacing, do_shift=True):
    frequency_spacing = 1 / sampling_spacing / num_samples
    frequencies = [frequency_spacing * n for n in range(num_samples)]
    if do_shift:
        frequencies_shifted = np.fft.fftshift(frequencies)
        dc_index = np.where(frequencies_shifted == 0)[0][0]
        frequencies = [f - frequencies[dc_index] for f in frequencies]
    return frequencies


def running_mean(x, n=5):
    return np.convolve(x, np.ones((n,))/n)[(n-1):]


def smooth(x, window_size=5):
    # x: NumPy 1-D array containing the data to be smoothed
    # window_size: smoothing window size, must be odd number
    # https://stackoverflow.com/questions/40443020/matlabs-smooth-implementation-n-point-moving-average-in-numpy-python
    out0 = np.convolve(x, np.ones(window_size, dtype=int), 'valid') / window_size
    r = np.arange(1, window_size-1, 2)
    start = np.cumsum(x[:window_size-1])[::2]/r
    stop = (np.cumsum(x[:-window_size:-1])[::2]/r)[::-1]
    return np.concatenate((start, out0, stop))


def find_x_of_threshold(x, y, y_threshold):
    bin_thr = np.argmax((y - y_threshold) < 0)
    bin_min = max(bin_thr - 1, 0)
    bin_max = min(bin_thr + 1, len(y) - 1)
    # upsample to obtain sub-integer resolution
    num_upsampling_bins = 50
    x_upsampled = np.linspace(x[bin_min], x[bin_max], num_upsampling_bins)
    y_upsampled = np.interp(x_upsampled, x, y)
    bin_thr = np.argsort(np.abs(y_upsampled - y_threshold))[0]
    return x_upsampled[bin_thr]


def radial_profile(y_data, r_data, r_bins, r_range=None, fill_value=None):
    if not isinstance(y_data, list):
        y_data = [y_data]
    # r_bins and r_range work as the corresponding parameters of numpy.histogram_bin_edges
    bin_edges = np.histogram_bin_edges(r_data, bins=r_bins, range=r_range)
    bin_index = np.digitize(r_data, bin_edges)
    # loop to average bin contributions
    y_values, v_values = np.zeros(bin_edges.size), np.zeros(bin_edges.size)
    for b in range(bin_edges.size):
        bin_contributors = np.array([])
        for y in y_data:
            bin_contributors = np.append(bin_contributors, y[bin_index == b])
        if len(bin_contributors) > 0:  # separate the two cases to avoid numpy warnings in the output
            y_values[b] = np.mean(bin_contributors)
            v_values[b] = np.var(bin_contributors)
        else:
            y_values[b] = None
            v_values[b] = None
    # interpolate bins with 'None' with values from neighbors
    nans = np.isnan(y_values)
    if fill_value is None:
        y_values[nans] = np.interp(bin_edges[nans], bin_edges[~nans], y_values[~nans])
        v_values[nans] = np.interp(bin_edges[nans], bin_edges[~nans], v_values[~nans])
    else:
        y_values[nans] = np.interp(bin_edges[nans], bin_edges[~nans], y_values[~nans], left=fill_value, right=fill_value)
        v_values[nans] = np.interp(bin_edges[nans], bin_edges[~nans], v_values[~nans], left=fill_value, right=fill_value)
    return bin_edges, y_values, v_values


def find_weighted_center(image):
    mesh_x, mesh_y = np.meshgrid(range(len(image[0])), range(len(image)))
    total = np.sum(image)
    cx = np.sum(np.multiply(mesh_x, image)) / total
    cy = np.sum(np.multiply(mesh_y, image)) / total
    return cx, cy


def find_circles(numpy_image, expected_radius_px, tolerance_px=1):
    """
    Return a list of coordinates for circles matching the desired radius
    """
    circles = []
    img = numpy_image.astype(np.uint8)
    ret, thrimg = cv.threshold(img, 127, 255, 0)
    # from actilib.helpers.display import display_pixels
    # display_pixels(thrimg)
    thr = cv.adaptiveThreshold(img, 255, cv.ADAPTIVE_THRESH_GAUSSIAN_C, cv.THRESH_BINARY, 11, 2)
    contours, hierarchy = cv.findContours(thr, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
    for c in contours:
        [x, y], r = cv.minEnclosingCircle(c)
        if r - tolerance_px < expected_radius_px < r + tolerance_px:
            circles.append([x, y, r])
    return circles
