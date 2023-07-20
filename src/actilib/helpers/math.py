import math
import numpy as np


def deg_from_rad(rad):
    return rad * 360 / (2 * math.pi)


def rad_from_deg(deg):
    return deg * 2 * math.pi / 360.0


def cart2pol(x, y):
    return np.arctan2(y, x), np.sqrt(x**2 + y**2)


def pol2cart(theta, rho):
    return rho * np.cos(theta), rho * np.sin(theta)


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


def find_x_of_threshold(x, y, y_threshold):
    bin_thr = np.argsort(np.abs(y - y_threshold))[0]  # approximate position (is an integer)
    bin_min = max(bin_thr - 1, 0)
    bin_max = min(bin_thr + 1, len(y) - 1)
    # upsample to obtain sub-integer resolution
    num_upsampling_bins = 50
    x_upsampled = np.linspace(x[bin_min], x[bin_max], num_upsampling_bins)
    y_upsampled = np.interp(x_upsampled, x, y)
    bin_thr = np.argsort(np.abs(y_upsampled - y_threshold))[0]
    return x_upsampled[bin_thr]


def radial_profile(y_data, r_data, r_bins, r_range=None):
    # r_bins and r_range work as the corresponding parameters of numpy.histogram_bin_edges
    bin_edges = np.histogram_bin_edges(r_data, bins=r_bins, range=r_range)
    bin_index = np.digitize(r_data, bin_edges)
    # loop to average bin contributions
    y_values, v_values = np.zeros(bin_edges.size), np.zeros(bin_edges.size)
    for b in range(len(bin_edges)):
        bin_contributors = y_data[bin_index == b]
        if len(bin_contributors) > 0:  # separate the two cases to avoid numpy warnings in the output
            y_values[b] = np.mean(bin_contributors)
            v_values[b] = np.var(bin_contributors)
        else:
            y_values[b] = None
            v_values[b] = None
    # interpolate bins with 'None' with values from neighbors
    nans = np.isnan(y_values)
    y_values[nans] = np.interp(bin_edges[nans], bin_edges[~nans], y_values[~nans])
    v_values[nans] = np.interp(bin_edges[nans], bin_edges[~nans], v_values[~nans])
    return bin_edges, y_values, v_values


def esf2ttf(esf, bin_width, num_samples=256, hann_window=15):
    # preparation: we search the two bins corresponding to 15% and 85% of the ESF curve
    # and we calculate the extremities of the Hann window in terms of bin indexes
    esf_min = min(esf)
    esf_max = max(esf)
    esf_mid = (esf_max + esf_min) / 2.0  # middle value
    esf_15p = esf_min + 0.15 * (esf_max - esf_min)
    esf_85p = esf_min + 0.85 * (esf_max - esf_min)
    esf_shifted_sorted_indexes = np.argsort(np.abs(esf - esf_mid))
    bin_mid = esf_shifted_sorted_indexes[0]  # bin of middle value
    if np.mean(esf[:bin_mid]) > np.mean(esf[bin_mid:]):  # ESF higher at the left -> roi_hu higher than background?
        bin_15p = np.asarray(esf < esf_15p).nonzero()[0][1]
        bin_85p = np.asarray(esf > esf_85p).nonzero()[0][-1]
    else:
        bin_15p = np.asarray(esf < esf_15p).nonzero()[0][-1]
        bin_85p = np.asarray(esf > esf_85p).nonzero()[0][1]
    bin_win = hann_window * abs(bin_85p - bin_15p)
    bin_hann_min = max(bin_mid - bin_win, 0)
    bin_hann_max = min(bin_mid + bin_win, len(esf) - 2)  # additional -1 because LSF will have 1 bin less
    # derivation -> LSF
    lsf = np.gradient(esf)
    # Hann smoothing (https://en.wikipedia.org/wiki/Hann_function)
    hann = np.zeros(lsf.size)
    hann[bin_hann_min:bin_hann_max] = np.hanning(bin_hann_max - bin_hann_min)
    lsf = np.multiply(lsf, hann)
    # finally calculating the TTF
    ttf = np.abs(np.fft.fftn(lsf))
    ttf = ttf[0:math.floor(len(ttf)/2)]  # cutting second half of array
    ttf = ttf / ttf[0]  # normalisation
    frq = np.linspace(0, 0.5 / bin_width, len(ttf))
    # resampling
    frq_resampled = np.linspace(0, 2.0, num_samples)
    ttf_resampled = np.interp(frq_resampled, frq, ttf)
    return frq_resampled, ttf_resampled, lsf
