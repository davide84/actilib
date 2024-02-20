import math
import numpy as np
from actilib.helpers.math import radial_profile, find_x_of_threshold
from actilib.analysis.rois import get_masked_image


def esf2ttf(esf, bin_width, num_samples=256, hann_window=15):
    # derivation -> LSF
    lsf = np.gradient(esf)
    # Hann smoothing (https://en.wikipedia.org/wiki/Hann_function)
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
        bin_15p = np.asarray(esf < esf_15p).nonzero()[0][0]
        bin_85p = np.asarray(esf > esf_85p).nonzero()[0][-1]
    else:
        bin_15p = np.asarray(esf < esf_15p).nonzero()[0][-1]
        bin_85p = np.asarray(esf > esf_85p).nonzero()[0][0]
    bin_win = hann_window * abs(bin_85p - bin_15p)
    bin_hann_min = max(bin_mid - bin_win, 0)
    bin_hann_max = min(bin_mid + bin_win, len(esf) - 2)  # additional -1 because LSF will have 1 bin less
    hann = np.zeros(lsf.size)
    hann[bin_hann_min:bin_hann_max] = np.hanning(bin_hann_max - bin_hann_min)
    lsf = np.multiply(lsf, hann)
    # finally calculating the TTF
    ttf = np.abs(np.fft.fftn(lsf))
    ttf = ttf[0:math.floor(len(ttf)/2)]  # cutting second half of array
    ttf = ttf / ttf[0]
    frq = np.linspace(0, 0.5 / bin_width, len(ttf))
    # resampling
    frq_resampled = np.linspace(0, 2.0, num_samples)
    ttf_resampled = np.interp(frq_resampled, frq, ttf)
    return frq_resampled, ttf_resampled, lsf


def calculate_roi_ttf(pixels, roi, pixel_size_xy_mm):
    pixel_size_mm = pixel_size_xy_mm[0]  # we assume square pixels otherwise the radius in mm is a mess to calculate...
    # prepare masks and masked images
    # - to calculate the ROI average HU we consider a region that is 95% of the radius
    #   if the ROI is uniform it cuts away border effects, if the ROI is not uniform then... whatever
    # - to calculate the background values we consider a region between 110% and 150% of the radius
    #   hoping that it is clean... we could play with quantiles to filter out stuff but then it would
    #   rely on assumptions on the ROI structure... of course the whole concept of 'background' is
    #   arbitrary if we only rely on the ROI position...
    #   For proper noise calculations one should define a noise ROI at an appropriate location.
    mask_fgd = roi.get_annular_mask(pixels, radius_outer=roi.radius() * 0.9)
    mask_bgd = roi.get_annular_mask(pixels, radius_inner=roi.radius() * 1.1, radius_outer=roi.radius() * 1.7)
    image_masked_fgd = get_masked_image(pixels, mask_fgd)
    image_masked_bgd = get_masked_image(pixels, mask_bgd)
    fgd = image_masked_fgd.mean()
    std = image_masked_fgd.std()
    bgd = image_masked_bgd.mean()
    noi = image_masked_bgd.std()
    cnt = fgd - bgd
    cnr = abs(cnt / noi)
    # crop image and subtract background
    crop_margin = roi.radius()  # so that we have some background around the ROI
    [i_t, i_b, i_l, i_r] = roi.indexes_tblr(margin_px=crop_margin)
    img_crop = pixels[i_t:i_b, i_l:i_r] - bgd
    img_radi = roi.get_distance_from_center(pixels)  # needs accurate roi center
    img_radi = img_radi[i_t:i_b, i_l:i_r] * pixel_size_mm  # radii must be in mm or the frequencies will be wrong!
    # calculate radial profile
    bin_scale = 10  # arbitrary - the higher, the more detailed the ESF estimation
    bin_width = pixel_size_mm / bin_scale
    bin_edges = np.arange(0, 2 * pixel_size_mm * roi.radius(), bin_width)
    distance, esf, variance = radial_profile(img_crop, img_radi, r_bins=bin_edges)
    # TODO: checks and cleanup of ESF (see papers)
    # calculate TTF from ESF
    frq, ttf, lsf = esf2ttf(esf, bin_width)
    f10 = find_x_of_threshold(frq, ttf, 0.1)
    f50 = find_x_of_threshold(frq, ttf, 0.5)
    return frq, ttf, {'bgd': bgd, 'fgd': fgd, 'std': std, 'cnt': cnt, 'noi': noi, 'cnr': cnr,
                      'esf': esf, 'lsf': lsf, 'f10': f10, 'f50': f50}


def ttf_properties(dicom_images, rois, average_images=True):
    if not isinstance(dicom_images, list):
        dicom_images = [dicom_images]
    if not isinstance(rois, list):
        rois = [rois]
    pixel_size_xy_mm = np.array(dicom_images[0]['header'].PixelSpacing)
    images = []
    for image in dicom_images:
        images.append(image['pixels'])
    if average_images:
        images = [np.mean(images, axis=0)]
    # loop over ROIs and images
    ret = []
    for i_roi, roi in enumerate(rois):
        # (!) in "numpy images" the 1st coordinate is y
        fgd_list = []
        std_list = []
        bgd_list = []
        cnt_list = []
        cnr_list = []
        noi_list = []
        # re-estimate center (precision needed for radial profile calculation)
        # we do it only once on the middle image, which should contain clear structures
        roi.auto_adjust_center(images[int(len(images)/2)])
        for i_image, image in enumerate(images):
            frq, ttf, other = calculate_roi_ttf(image, roi, pixel_size_xy_mm)
            fgd_list.append(other['fgd'])
            std_list.append(other['std'])
            bgd_list.append(other['bgd'])
            cnt_list.append(other['cnt'])
            cnr_list.append(other['cnr'])
            noi_list.append(other['noi'])
        ret.append({
            'esf': other['esf'].tolist(),
            'lsf': other['lsf'].tolist(),
            'ttf': ttf.tolist(),
            'frq': frq.tolist(),
            'f10': other['f10'],
            'f50': other['f50'],
            'huavg': other['fgd'],
            'hustd': other['std'],
            'hubgd': other['bgd'],
            'noise': other['noi'],
            'contrast': other['cnt']
        })
    return ret
