import numpy as np
import matplotlib.pyplot as plt
from actilib.analysis.rois import SquareROI
from actilib.analysis.nps import noise_properties
from actilib.helpers.math import get_polar_mesh

# base variables
IMAGE_PXS = 256
IMAGE_AVG = 128
NOISE_AMP = 20
PIXEL_MM = 1
header = type('obj', (object,), {'PixelSpacing': [1, 1]})  # pixel spacing in mm
ROI = SquareROI(IMAGE_PXS, int(IMAGE_PXS/2), int(IMAGE_PXS/2))
IMAGE_UNI = IMAGE_AVG * np.ones((IMAGE_PXS, IMAGE_PXS))
_, MESH_F = get_polar_mesh(np.fft.fftshift(np.fft.fftfreq(IMAGE_PXS, PIXEL_MM)))


def cart2pol(x, y):
    # np.hypot(x, y) equivalent to np.sqrt(x**2 + y**2) but less (or no) risk of ever overflowing
    return np.arctan2(y, x), np.hypot(x, y)


# https://stackoverflow.com/questions/33933842/how-to-generate-noise-in-frequency-range-with-numpy
# def fftnoise(f):
#     f = np.array(f, dtype='complex')
#     Np = (len(f) - 1) // 2
#     phases = np.random.rand(Np) * 2 * np.pi
#     phases = np.cos(phases) + 1j * np.sin(phases)
#     f[1:Np+1] *= phases
#     f[-1:-1-Np:-1] = np.conj(f[1:Np+1])
#     return np.fft.ifft(f).real
#
#
# def band_limited_noise(min_freq, max_freq, samples=IMAGE_PXS, samplerate=10):
#     freqs = np.abs(np.fft.fftfreq(samples, 1/samplerate))
#     f = np.zeros((samples, samples))
#     idx = np.where(np.logical_and(freqs >= min_freq, freqs <= max_freq))[0]
#     f[idx] = 1
#     return fftnoise(f)


def add_band_noise(image, fmin, fmax, amplitude):
    noise = np.zeros(MESH_F.shape)
    mask = np.where((fmin < MESH_F) & (MESH_F < fmax))
    noise[mask] = (amplitude / (fmax - fmin))**2
    img_fourier = np.fft.fftshift(np.fft.fft2(image))
    img_fourier = img_fourier + noise
    img_return = np.abs(np.fft.ifft2(np.fft.ifftshift(img_fourier)))
    return img_return, noise
    from actilib.helpers.math import subtract_2d_poly_mean
    return subtract_2d_poly_mean(img_return)
    return np.abs(img_fourier)


def plot_example(where, patch_size, patch_dist, amplitude=NOISE_AMP):
    axs_img = where[0][where[1]][where[2]]
    axs_fou = where[0][where[1]][where[2]+1]
    axs_nps = where[0][where[1]][where[2]+2]
    image = np.ones((IMAGE_PXS, IMAGE_PXS), dtype=np.int8) * IMAGE_AVG
    if patch_size == 0:  # forcing HF noise in Fourier domain
        # random_noise = IMAGE_AVG + (NOISE_AMP * np.random.rand(IMAGE_PXS, IMAGE_PXS) * 2 - 1).astype(int)
        # img_fourier[mask] += np.random.randint(low=-NOISE_AMP, high=1+NOISE_AMP, size=image[mask].size)
        if patch_dist == 0:
            axs_img.set_title('Fourier LF noise')
            image, img_noise = add_band_noise(image, 0.05, 0.15, NOISE_AMP)
        elif patch_dist == 1:
            axs_img.set_title('Fourier MF noise')
            img_fourier = np.fft.fftshift(np.fft.fft2(image))
            img_fourier[(0.25 < MESH_F) & (MESH_F < 0.35)] = amplitude * NOISE_AMP
            image = np.abs(np.fft.ifft2(np.fft.ifftshift(img_fourier)))
        elif patch_dist == 2:
            axs_img.set_title('Fourier HF noise')
            img_fourier = np.fft.fftshift(np.fft.fft2(image))
            img_fourier[(0.5 < MESH_F) & (MESH_F < 0.6)] = amplitude * NOISE_AMP
            image = np.abs(np.fft.ifft2(np.fft.ifftshift(img_fourier)))
            image = np.fft.fftshift(image)
        else:  # random noise
            axs_img.set_title('random noise (+-{})'.format(amplitude))
            image = IMAGE_AVG + amplitude * (np.random.rand(IMAGE_PXS, IMAGE_PXS) * 2 - 1)
            image[0, :] = IMAGE_AVG
            image[-1, :] = IMAGE_AVG
            image[:, 0] = IMAGE_AVG
            image[:, -1] = IMAGE_AVG
    else:
        num_patches = int(IMAGE_PXS / (patch_size + patch_dist))
        axs_img.set_title('{} random patches'.format(num_patches**2))
        margin = int(patch_dist / 2)
        for px in range(num_patches):
            x0 = margin + (patch_size + patch_dist) * px
            x1 = margin + (patch_size + patch_dist) * px + patch_size
            for py in range(num_patches):
                y0 = margin + (patch_size + patch_dist) * py
                y1 = margin + (patch_size + patch_dist) * py + patch_size
                image[y0:y1, x0:x1] += amplitude * (np.random.randint(2) * 2 - 1)
    noise = noise_properties({'header': header, 'pixels': image}, ROI)
    # print(noise['noise'])
    fig, axs = plt.subplots(2, 2, figsize=(8, 8))
    axs_noi = axs[0][0]
    axs_fou = axs[0][1]
    axs_img = axs[1][0]
    axs_nps = axs[1][1]
    axs_img.imshow(image, cmap='gray', vmin=IMAGE_AVG-2*NOISE_AMP, vmax=IMAGE_AVG+2*NOISE_AMP)
    axs_img.axis('off')
    axs_noi.imshow(img_noise, cmap='gray')
    axs_noi.axis('off')
    axs_fou.imshow(noise['nps_2d'], cmap='gray')
    axs_fou.axis('off')
    axs_nps.plot(noise['f1d'], noise['nps_1d'])
    axs_nps.set_title('noise ($\sigma^2$) = {:.2f}'.format(noise['noise']))
    axs_nps.set_xlabel('frequency [mm$^{-1}$]')
    plt.show()


# plotting
fig, axs = plt.subplots(4, 6, figsize=(12, 5))
# plot_example((axs, 0, 0), 32, 32)
# plot_example((axs, 1, 0), 8, 8)
# plot_example((axs, 2, 0), 2, 2)
# plot_example((axs, 3, 0), 1, 1)
plot_example((axs, 0, 0), 0, 0, 415)
# plot_example((axs, 1, 0), 0, 1, 220)
# plot_example((axs, 2, 0), 0, 2, 240)
# plot_example((axs, 3, 0), 0, None)
# plt.tight_layout()
# plt.show()



