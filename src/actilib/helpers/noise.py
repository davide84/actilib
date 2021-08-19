import numpy as np
from actilib.helpers.math import fft_frequencies, subtract_2d_poly_mean, radial_profile, smooth


def background_properties(dicom_images, roi_series, pixel_size, fft_samples=128):
    try:
        pixel_size_x = pixel_size[0]
        pixel_size_y = pixel_size[1]
    except TypeError:
        pixel_size_x = pixel_size
        pixel_size_y = pixel_size
    # prepare variables
    fft_size = [fft_samples, fft_samples]
    freq_x = fft_frequencies(fft_samples, pixel_size_x)
    freq_y = fft_frequencies(fft_samples, pixel_size_y)
    dfreq_x = 1 / (pixel_size_x * fft_samples)
    dfreq_y = 1 / (pixel_size_y * fft_samples)
    hu_series = []
    nps_series = []
    var_series = []
    # loop over ROIs and images
    for i_roi, roi in enumerate(roi_series):
        [y1, y2, x1, x2] = roi.yx_indexes()
        norm = np.prod(pixel_size) / (roi.size() ** 2)
        for i_image, dicom_image in enumerate(dicom_images):
            roi_pixels = dicom_image[y1-1:y2, x1-1:x2]  # (!) in "numpy images" the 1st coordinate is y
            # do stuff with the ROI pixels
            hu = np.mean(roi_pixels)
            hu_series.append(hu)
            # subtract mean value
            roi_sub = subtract_2d_poly_mean(roi_pixels)
            nps = norm * np.abs(np.fft.fftshift(np.fft.fftn(roi_sub, fft_size))) ** 2
            nps_series.append(nps)
            var_series.append(np.sum(nps) * dfreq_x * dfreq_y)
    # applying formula for 2D NPS, then radial profile
    nps_2d = np.mean(np.array(nps_series), axis=0)
    nps_freqs, nps_1d, nps_var = radial_profile(nps_2d, freq_x, freq_y)
    nps_smooth = smooth(nps_1d)
    peak_freq = nps_freqs[np.argmax(nps_smooth)]
    mean_freq = np.sum(nps_1d * nps_freqs / sum(nps_1d))
    return {
        "hu": np.mean(hu_series),
        "noise": np.sqrt(np.mean(var_series)),
        "noise_std": np.std(np.sqrt(var_series)),
        "f1d": nps_freqs,
        "f2d_x": freq_x,
        "f2d_y": freq_y,
        "fpeak": peak_freq,
        "fmean": mean_freq,
        "nps_1d": nps_1d,
        "nps_2d": nps_2d
    }
