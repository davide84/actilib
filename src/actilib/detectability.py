import math
import numpy as np
import scipy.interpolate
from helpers.math import cart2pol


def get_dprime_default_params():
    # coeff is the exponent of the designer shape or blur factor of the gaussian shape (is not used for flat shapes)
    return {
        "profile_type": 'Designer',  # task.profileType | 2D shape of the object
        "diameter_mm": 5,            # task.diameter (lesion diameter for simulations)
        "coeff": 1,                  # task.n
        "contrast_hu": 15,           # task.Contrast
        "pixel_number": 300,         # task.N
        "pixel_size_mm": 0.05,       # task.psize
        "fov_mm": 15                 # task.FOV
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


def get_fft_frequency(pixel_size_mm, pixel_number):
    spatial_frequency = 1.0 / pixel_size_mm
    frequency_spacing = spatial_frequency / pixel_number
    indices = np.arange(pixel_number)
    unshifted_frequencies = indices * frequency_spacing
    shifted_frequencies = np.fft.fftshift(unshifted_frequencies)
    constant_index = np.where(shifted_frequencies == 0)[0][0]
    unshifted_frequencies = unshifted_frequencies - unshifted_frequencies[constant_index]
    return unshifted_frequencies


def resample_2d_ttf(data_freq, data_ttf, pixel_size_mm, pixel_number):
    """Resample a TTF array to match a task meshgrid"""
    freq_x = get_fft_frequency(pixel_size_mm, pixel_number)
    freq_y = freq_x
    mesh_x, mesh_y = np.meshgrid(freq_x, freq_y)
    mesh_a, mesh_r = cart2pol(mesh_x, mesh_y)
    ttf_resampled = np.interp(mesh_r, data_freq['ttf_f'], data_ttf['TTF'], 0, 0)  # linear by definition
    return ttf_resampled


def resample_2d_nps(data_freq, data_nps, pixel_size_mm, pixel_number, mode='2D'):
    """Resample a NPS array to match a task meshgrid"""
    freq_x = get_fft_frequency(pixel_size_mm, pixel_number)
    freq_y = freq_x
    mesh_x, mesh_y = np.meshgrid(freq_x, freq_y)
    if mode == 'radial':
        mesh_a, mesh_r = cart2pol(mesh_x, mesh_y)
        nps_resampled = np.interp(mesh_r, data_freq['nps_f'], data_nps['NPS'], 0, 0)  # linear by definition
    else:  # default equivalent to mode == '2D'
        ip = scipy.interpolate.interp2d(data_freq['nps_fx'], data_freq['nps_fy'], data_nps['NPS_2D'],
                                        kind='linear', fill_value=0.0)
        nps_resampled = ip(freq_x, freq_y)
    # Scale the NPS as needed to maintain the noise variance from he original NPS
    spacing_x = freq_x[1] - freq_x[0]
    spacing_y = freq_y[1] - freq_y[0]  # redundant but explicit for clarity
    scale_factor = (data_nps['noise'] ** 2) / (np.sum(nps_resampled) * spacing_x * spacing_y)
    nps_resampled = scale_factor * nps_resampled
    return nps_resampled


def calculate_dprime(data_freq, data_nps, data_ttf, params=get_dprime_default_params()):
    pixel_size_sq = params['pixel_size_mm'] ** 2
    task_image = calculate_task_image(params)
    weights = np.fft.fftshift(abs(pixel_size_sq * np.fft.fftn(task_image)) ** 2)
    ttf_resampled = resample_2d_ttf(data_freq, data_ttf, params['pixel_size_mm'], params['pixel_number'])
    nps_resampled = resample_2d_nps(data_freq, data_nps, params['pixel_size_mm'], params['pixel_number'])
    eye_filter = np.ones(params['pixel_number'])  # TODO implement get.EyeFilter as in imquest_Dprime.m
    internal_noise = np.zeros(params['pixel_number'])  # TODO implement get.InternalNoise as in imquest_Dprime.m
    freq_spacing_coeff = (1.0 / (params['pixel_size_mm'] * params['pixel_number'])) ** 2
    # finally, the d' calculation
    partial = weights * (ttf_resampled ** 2)
    numerator = (np.sum(partial * (eye_filter ** 2)) * freq_spacing_coeff) ** 2
    denominator = np.sum(partial * (eye_filter ** 4) * nps_resampled + internal_noise) * freq_spacing_coeff
    d_prime = math.sqrt(numerator / denominator)
    return d_prime

