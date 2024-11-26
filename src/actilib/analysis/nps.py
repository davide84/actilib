import numpy as np
from actilib.helpers.math import subtract_2d_poly_mean, radial_profile, smooth, get_polar_mesh


def calculate_roi_nps2d(pixels, roi, pixel_size_xy_mm, fft_samples=128):
    norm = np.prod(pixel_size_xy_mm) / (roi.size() ** 2)
    roi_image = roi.get_cropped_image(pixels)
    roi_sub = subtract_2d_poly_mean(roi_image)
    nps = norm * np.abs(np.fft.fftshift(np.fft.fft2(roi_sub, (fft_samples, fft_samples)))) ** 2
    return nps, np.mean(roi_image)


def noise_properties(dicom_images, roi, fft_samples=128):
    if not isinstance(dicom_images, list):
        dicom_images = [dicom_images]
    pixel_size_xy_mm = np.array(dicom_images[0]['header'].PixelSpacing)
    pixel_size_x_mm, pixel_size_y_mm = pixel_size_xy_mm
    images = []
    for image in dicom_images:
        images.append(image['pixels'])
    # prepare variables
    freq_x = np.fft.fftshift(np.fft.fftfreq(fft_samples, pixel_size_x_mm))
    freq_y = np.fft.fftshift(np.fft.fftfreq(fft_samples, pixel_size_y_mm))
    dfreq_x = 1 / (pixel_size_x_mm * fft_samples)
    dfreq_y = 1 / (pixel_size_y_mm * fft_samples)
    # loop over images
    hu_series = []
    nps_series = []
    var_series = []
    for image in images:
        nps, hu = calculate_roi_nps2d(image, roi, pixel_size_xy_mm, fft_samples=fft_samples)
        hu_series.append(hu)
        nps_series.append(nps)
        var_series.append(np.sum(nps) * dfreq_x * dfreq_y)
    # applying formula for 2D NPS, then radial profile
    nps_2d = np.mean(np.array(nps_series), axis=0)
    _, mesh_r = get_polar_mesh(freq_x, freq_y)
    nps_freqs, nps_1d, nps_var = radial_profile(nps_2d, mesh_r, r_bins=nps_2d.shape[0], fill_value=0.0)
    peak_freq = nps_freqs[np.argmax(smooth(nps_1d))]
    mean_freq = np.sum(nps_1d * nps_freqs / sum(nps_1d))
    return {  # returning lists instead of ndarrays to not expose numpy dependencies (e.g. JSON serialization)
        'huavg': np.mean(hu_series),
        'noise': np.sqrt(np.mean(var_series)),
        'noise_std': np.std(np.sqrt(var_series)),
        'f1d': nps_freqs.tolist(),
        'f2d_x': freq_x.tolist(),
        'f2d_y': freq_y.tolist(),
        'fpeak': peak_freq,
        'fmean': mean_freq,
        'nps_1d': nps_1d.tolist(),
        'nps_2d': nps_2d.tolist()
    }

