import matplotlib.pyplot as plt
import numpy as np

from actilib.analysis.detectability import fft_frequencies, get_dprime_default_params, get_eye_filter, calculate_task_image



params = get_dprime_default_params()
print(params)
params['view_model'] = 'NPWE'
params['task_pixel_number'] = 128
params['task_pixel_size_mm'] = 0.488281011581  # from DICOM header
params['view_pixel_size_mm'] = params['task_pixel_size_mm']
params['view_distance_mm'] = 400

freq_1d = fft_frequencies(params['task_pixel_number'], params['task_pixel_size_mm'])
mm_1d = params['task_pixel_size_mm'] * np.arange(-params['task_pixel_number']/2, params['task_pixel_number']/2)
task_image = calculate_task_image(params)
filter = get_eye_filter(params)

#plt.plot(mm_1d, task_image[150])
print(freq_1d)
plt.plot(freq_1d, filter[int(len(filter)/2)])
plt.xlim([0, 0.6])
plt.ylim([0, 1.1])
plt.title('Eye Filter - Task Pixel Number: {}'.format(params['task_pixel_number']))
plt.show()
print(params)

