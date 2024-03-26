import math
import numpy as np
import scipy.interpolate
from actilib.helpers.math import cart2pol, fft_frequencies


def get_dprime_default_params():
    return {
        "task_profile": 'Designer',  # 2D shape of the object
        "task_coeff": 1,             # exponent of shape (Designer profile) or blur factor (Gaussian profile)
        "task_diameter_mm": 10,      # lesion diameter for simulations [mm]
        "task_contrast_hu": 15,      # contrast of the ROI [HU]
        "task_pixel_number": 300,    #
        "task_pixel_size_mm": 0.05,  # pixel size for the task function
        "view_pixel_size_mm": 0.2,   # pixel size for the display (monitor resolution)
        "view_zoom": 1,              # magnification factor to simulate display
        "view_distance_mm": 400,     #
        "view_model": 'NPW'          # ['NPW', 'NPWE']
    }


def calculate_radial_mesh(params):
    fov_mm = params["task_pixel_number"] * params["task_pixel_size_mm"]
    x = [(i * params['task_pixel_size_mm'] - fov_mm / 2.0) for i in range(params['task_pixel_number'])]
    mesh_x, mesh_y = np.meshgrid(x, x)
    mesh_a, mesh_r = cart2pol(mesh_x, mesh_y)
    return mesh_r


def calculate_task_image(params):
    mesh_r = calculate_radial_mesh(params)
    radius = params['task_diameter_mm'] / 2.0
    if params['task_profile'] == 'Gaussian':
        return (params['task_contrast_hu'] / 2) * (1 - math.erf((mesh_r - radius) / params['task_coeff']))
    elif params['task_profile'] == 'Flat':
        return params['task_contrast_hu'] if mesh_r <= radius else 0.0
    elif params['task_profile'] != 'Designer':
        print('Profile type "' + params['task_profile'] + '" not supported, using "Designer"')
    contrast_weight = ((1 - ((mesh_r / radius) ** 2)) ** params['task_coeff']) * params['task_contrast_hu']
    contrast_weight[mesh_r > radius] = 0
    return contrast_weight


def resample_2d_ttf(data_freq, data_ttf, dest_freq):
    """Resample a TTF array to match a meshgrid"""
    mesh_x, mesh_y = np.meshgrid(dest_freq, dest_freq)
    mesh_a, mesh_r = cart2pol(mesh_x, mesh_y)
    return np.interp(mesh_r, data_freq['ttf_f'], data_ttf['ttf'], 0, 0)  # linear by definition


def resample_2d_nps(data_freq, data_nps, dest_freq, mode='2D'):
    """Resample a NPS array to match a meshgrid"""
    if mode == 'radial':
        mesh_x, mesh_y = np.meshgrid(dest_freq, dest_freq)
        mesh_a, mesh_r = cart2pol(mesh_x, mesh_y)
        nps_resampled = np.interp(mesh_r, data_freq['nps_f'], data_nps['nps_1d'], 0, 0)  # linear by definition
    else:  # default equivalent to mode == '2D'
        ip = scipy.interpolate.interp2d(data_freq['nps_fx'], data_freq['nps_fy'], data_nps['nps_2d'],
                                        kind='linear', fill_value=0.0)
        nps_resampled = ip(dest_freq, dest_freq)
    # Scale the NPS as needed to maintain the noise variance from he original NPS
    freq_spacing = dest_freq[1] - dest_freq[0]
    scale_factor = (data_nps['noise'] ** 2) / (np.sum(nps_resampled) * (freq_spacing ** 2))
    nps_resampled = scale_factor * nps_resampled
    return nps_resampled


def get_eye_filter(freq_1d, params):
    if params['view_model'] == 'NPWE':
        # the following three parameters are hardcoded because nobody is actually changing them
        n = 1.5
        c = 3.22  # deg^-1
        a = 0.68
        distance_mm = params['view_distance_mm']  # mm, visual distance
        fov_mm = params["task_pixel_number"] * params["task_pixel_size_mm"]  # (!) TASK PXSIZE
        display_mm = params['view_zoom'] * params["task_pixel_number"] * params["view_pixel_size_mm"]  # (!) VIEW PXSIZE
        freq_2d_x, freq_2d_y = np.meshgrid(freq_1d, freq_1d)
        freq_2d_a, freq_2d_r = cart2pol(freq_2d_x, freq_2d_y)
        rho = freq_2d_r * fov_mm * distance_mm * np.pi / display_mm / 180
        filter = np.power(rho, 2*n) * np.exp(-c * 2 * np.power(rho, a))
        return filter / np.max(filter)
    return np.ones((len(freq_1d), len(freq_1d)))


def calculate_dprime(data_freq, data_nps, data_ttf, params=get_dprime_default_params()):
    task_image = calculate_task_image(params)
    pixel_size_sq = params['task_pixel_size_mm'] ** 2
    weights = np.fft.fftshift(abs(pixel_size_sq * np.fft.fftn(task_image)) ** 2)
    freq_1d = fft_frequencies(params['task_pixel_number'], params['task_pixel_size_mm'])
    ttf_resampled = resample_2d_ttf(data_freq, data_ttf, freq_1d)
    nps_resampled = resample_2d_nps(data_freq, data_nps, freq_1d)
    eye_filter = get_eye_filter(freq_1d, params)
    internal_noise = np.zeros(params['task_pixel_number'])  # TODO implement noise calculation instead of null matrix
    freq_spacing_coeff = (1.0 / (params['task_pixel_size_mm'] * params['task_pixel_number'])) ** 2
    # finally, the d' calculation
    partial = weights * (ttf_resampled ** 2)
    numerator = np.sum(partial * (eye_filter ** 2)) * freq_spacing_coeff
    denominator = math.sqrt(np.sum(partial * (eye_filter ** 4) * nps_resampled + internal_noise) * freq_spacing_coeff)
    return numerator / denominator

