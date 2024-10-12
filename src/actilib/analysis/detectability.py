import math
import numpy as np
from scipy.interpolate import RectBivariateSpline
from actilib.helpers.math import get_polar_mesh


def get_dprime_default_params():
    return {
        "task_profile": 'Flat',      # 2D shape of the object [Flat, Gaussian, Ogive]
        "task_profile_coeff": 1,     # blur factor (Gaussian profile) or exponent of shape (Ogive profile)
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
    mesh_a, mesh_r = get_polar_mesh(x)
    return mesh_r


def calculate_task_image(params):
    mesh_r = calculate_radial_mesh(params)
    radius = params['task_diameter_mm'] / 2.0
    if params['task_profile'] == 'Flat':
        task = np.zeros(mesh_r.shape)
        task[mesh_r <= radius] = params['task_contrast_hu']
    elif params['task_profile'] == 'Gaussian':
        task = (params['task_contrast_hu'] / 2) * (1 - math.erf((mesh_r - radius) / params['task_profile_coeff']))
    elif params['task_profile'] == 'Ogive':
        task = ((1 - ((mesh_r / radius) ** 2)) ** params['task_profile_coeff']) * params['task_contrast_hu']
        task[mesh_r > radius] = 0
    else:
        print('Profile type "' + params['task_profile'] + '" not supported, defaulting to "Flat"')
        task = calculate_task_image(dict(params, profile='Flat'))
    return task


def resample_2d_ttf(data_freq, data_ttf, dest_freq):
    """Resample a TTF array to match a meshgrid"""
    mesh_a, mesh_r = get_polar_mesh(dest_freq)
    return np.interp(mesh_r, data_freq['ttf_f'], data_ttf['ttf'], 0, 0)  # linear by definition


def resample_2d_nps(data_freq, data_nps, dest_freq, mode='2D'):
    """Resample a NPS array to match a meshgrid"""
    if mode == 'radial':
        mesh_a, mesh_r = get_polar_mesh(dest_freq)
        nps_resampled = np.interp(mesh_r, data_freq['nps_f'], data_nps['nps_1d'], 0, 0)  # linear by definition
    else:  # default equivalent to mode == '2D'
        r = RectBivariateSpline(data_freq['nps_fx'], data_freq['nps_fy'], data_nps['nps_2d'])
        nps_resampled = r(dest_freq, dest_freq)
    # Scale the NPS as needed to maintain the noise variance from the original NPS
    freq_spacing = dest_freq[1] - dest_freq[0]
    scale_factor = (data_nps['noise'] ** 2) / (np.sum(nps_resampled) * (freq_spacing ** 2))
    nps_resampled = scale_factor * nps_resampled
    return nps_resampled


def get_eye_filter(params, freq_1d=None):
    task_npx, task_psize = params['task_pixel_number'], params['task_pixel_size_mm']
    if params['view_model'] == 'NPWE':
        # the following three parameters are hardcoded because nobody is actually changing them (except c, in one paper)
        n = 1.5
        c = 3.22  # deg^-1
        a = 0.68
        distance_mm = params['view_distance_mm']  # mm, visual distance
        fov_mm = task_npx * task_psize  # (!) TASK PXSIZE
        display_mm = params['view_zoom'] * task_npx * params["view_pixel_size_mm"]  # (!) VIEW PXSIZE
        freq_1d = freq_1d if freq_1d is not None else np.fft.fftshift(np.fft.fftfreq(task_npx, task_psize))
        freq_2d_a, freq_2d_r = get_polar_mesh(freq_1d)
        rho = freq_2d_r * fov_mm * distance_mm * np.pi / display_mm / 180
        filter = np.power(rho, 2*n) * np.exp(-c * 2 * np.power(rho, a))
        return filter / np.max(filter)
    return np.ones((task_npx, task_npx))


def calculate_dprime(data_nps, data_ttf, params=get_dprime_default_params()):
    data_freq = {
        'nps_fx': data_nps['f2d_x'],
        'nps_fy': data_nps['f2d_y'],
        'nps_f': data_nps['f1d'],
        'ttf_f': data_ttf['frq']
    }
    task_image = calculate_task_image(params)
    pixel_size_sq = params['task_pixel_size_mm'] ** 2
    task_freq = np.fft.fftshift(abs(pixel_size_sq * np.fft.fftn(task_image)))
    freq_1d = np.fft.fftshift(np.fft.fftfreq(params['task_pixel_number'], params['task_pixel_size_mm']))
    ttf_resampled = resample_2d_ttf(data_freq, data_ttf, freq_1d)
    nps_resampled = resample_2d_nps(data_freq, data_nps, freq_1d)
    eye_filter = get_eye_filter(params, freq_1d)
    internal_noise = np.zeros(params['task_pixel_number'])  # TODO implement noise calculation instead of null matrix
    freq_spacing_coeff = (1.0 / (params['task_pixel_size_mm'] * params['task_pixel_number'])) ** 2
    # finally, the d' calculation
    common = task_freq ** 2 * (ttf_resampled ** 2)
    numerator = np.sum(common * (eye_filter ** 2)) * freq_spacing_coeff
    denominator = math.sqrt(np.sum(common * (eye_filter ** 4) * nps_resampled + internal_noise) * freq_spacing_coeff)
    return numerator / denominator

