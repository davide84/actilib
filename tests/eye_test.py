from actilib.analysis.detectability import get_eye_filter, get_dprime_default_params
import numpy as np
import matplotlib.pyplot as plt

params = get_dprime_default_params()
params['view_model'] = 'NPWE'
params['task_pixel_number'] = 300
params['task_pixel_size_mm'] = 0.5
params['view_pixel_size_mm'] = 0.5
params['view_zoom'] = 1
params['view_distance_mm'] = 400
freq_1d = np.fft.fftshift(np.fft.fftfreq(params['task_pixel_number'], params['task_pixel_size_mm']))

filter1 = get_eye_filter(params)

x_corr = params['view_distance_mm'] / (params['task_pixel_number'] * params['view_pixel_size_mm'])
filter2 = get_eye_filter(params, freq_1d / x_corr)

plt.plot(freq_1d, filter1[int(len(filter1)/2)])
plt.plot(x_corr*freq_1d, filter2[int(len(filter2)/2)])
plt.xlim(0, 2.5)
plt.show()

