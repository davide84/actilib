import math
import numpy as np
import scipy.interpolate
from actilib.helpers.math import cart2pol, fft_frequencies


def get_dprime_default_params():
    return {
        "profile_type": 'Designer',  # 2D shape of the object
        "diameter_mm": 5,            # lesion diameter for simulations [mm]
        "coeff": 1,                  # exponent of shape (Designer profile) or blur factor (Gaussian profile)
        "contrast_hu": 15,           # contrast of the ROI [HU]
        "pixel_number": 300,         #
        "pixel_size_mm": 0.05,       #
        "fov_mm": 15                 #
    }


def calculate_radial_mesh(params):
    x = [(i * params['pixel_size_mm'] - params['fov_mm'] / 2.0) for i in range(params['pixel_number'])]
    mesh_x, mesh_y = np.meshgrid(x, x)
    mesh_a, mesh_r = cart2pol(mesh_x, mesh_y)
    return mesh_r


def calculate_task_image(params):
    mesh_r = calculate_radial_mesh(params)
    radius = params['diameter_mm'] / 2.0
    if params['profile_type'] == 'Gaussian':
        return (params['contrast_hu'] / 2) * (1 - math.erf((mesh_r - radius) / params['coeff']))
    elif params['profile_type'] == 'Flat':
        return params['contrast_hu'] if mesh_r <= radius else 0.0
    elif params['profile_type'] != 'Designer':
        print('Profile type "' + params['profile_type'] + '" not supported, using "Designer"')
    contrast_weight = ((1 - ((mesh_r / radius) ** 2)) ** params['coeff']) * params['contrast_hu']
    contrast_weight[mesh_r > radius] = 0
    return contrast_weight


def resample_2d_ttf(data_freq, data_ttf, pixel_size_mm, pixel_number):
    """Resample a TTF array to match a meshgrid"""
    freq = fft_frequencies(pixel_number, pixel_size_mm)
    mesh_x, mesh_y = np.meshgrid(freq, freq)
    mesh_a, mesh_r = cart2pol(mesh_x, mesh_y)
    return np.interp(mesh_r, data_freq['ttf_f'], data_ttf['ttf'], 0, 0)  # linear by definition


def resample_2d_nps(data_freq, data_nps, pixel_size_mm, pixel_number, mode='2D'):
    """Resample a NPS array to match a meshgrid"""
    freq = fft_frequencies(pixel_number, pixel_size_mm)
    if mode == 'radial':
        mesh_x, mesh_y = np.meshgrid(freq, freq)
        mesh_a, mesh_r = cart2pol(mesh_x, mesh_y)
        nps_resampled = np.interp(mesh_r, data_freq['nps_f'], data_nps['nps_1d'], 0, 0)  # linear by definition
    else:  # default equivalent to mode == '2D'
        ip = scipy.interpolate.interp2d(data_freq['nps_fx'], data_freq['nps_fy'], data_nps['nps_2d'],
                                        kind='linear', fill_value=0.0)
        nps_resampled = ip(freq, freq)
    # Scale the NPS as needed to maintain the noise variance from he original NPS
    freq_spacing = freq[1] - freq[0]
    scale_factor = (data_nps['noise'] ** 2) / (np.sum(nps_resampled) * (freq_spacing ** 2))
    nps_resampled = scale_factor * nps_resampled
    return nps_resampled


def calculate_dprime(data_freq, data_nps, data_ttf, params=get_dprime_default_params()):
    pixel_size_sq = params['pixel_size_mm'] ** 2
    task_image = calculate_task_image(params)
    weights = np.fft.fftshift(abs(pixel_size_sq * np.fft.fftn(task_image)) ** 2)
    ttf_resampled = resample_2d_ttf(data_freq, data_ttf, params['pixel_size_mm'], params['pixel_number'])
    nps_resampled = resample_2d_nps(data_freq, data_nps, params['pixel_size_mm'], params['pixel_number'])
    eye_filter = np.ones(params['pixel_number'])  # TODO implement more eye filters other than identity matrix
    internal_noise = np.zeros(params['pixel_number'])  # TODO implement noise calculation instead of null matrix
    freq_spacing_coeff = (1.0 / (params['pixel_size_mm'] * params['pixel_number'])) ** 2
    # finally, the d' calculation
    partial = weights * (ttf_resampled ** 2)
    numerator = (np.sum(partial * (eye_filter ** 2)) * freq_spacing_coeff) ** 2
    denominator = np.sum(partial * (eye_filter ** 4) * nps_resampled + internal_noise) * freq_spacing_coeff
    d_prime = math.sqrt(numerator / denominator)
    return d_prime

