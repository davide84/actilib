import numpy as np
import matplotlib.pyplot as plt
from actilib.helpers.math import fft_frequencies, radial_profile, esf2ttf, find_x_of_threshold
from actilib.helpers.rois import get_masked_image
from actilib.helpers.display import display_image_with_rois


def calculate_image_ttf(pixels, roi, pixel_size):
    # prepare masks and masked images
    mask_fgd = roi.get_annular_mask(pixels, margin_outer=-roi.radius() * 0.1, margin_inner=-roi.radius())
    mask_bkg = roi.get_annular_mask(pixels, margin_outer=roi.radius(), margin_inner=roi.radius() * 0.8)
    image_masked_fgd = get_masked_image(pixels, mask_fgd)
    image_masked_bkg = get_masked_image(pixels, mask_bkg)
    fgd = image_masked_fgd.mean()
    bkg = image_masked_bkg.mean()
    noi = image_masked_bkg.std()
    cnt = fgd - bkg
    cnr = abs(cnt / noi)
    # crop image and subtract background
    crop_margin = roi.radius()  # so that we have some background around the ROI
    [i_t, i_b, i_l, i_r] = roi.indexes_tblr(margin_px=crop_margin)
    img_crop = pixels[i_t:i_b, i_l:i_r] - bkg
    img_radi = roi.get_distance_from_center(pixels)  # needs accurate roi center
    img_radi = img_radi[i_t:i_b, i_l:i_r] * pixel_size  # radii must be in mm or the frequencies will be wrong!
    # calculate radial profile
    bin_scale = 10  # arbitrary - the higher, the more detailed the ESF estimation
    bin_width = pixel_size / bin_scale
    bin_edges = np.arange(0, 2 * pixel_size * roi.radius(), bin_width)
    distance, esf, variance = radial_profile(img_crop, img_radi, r_bins=bin_edges)
    # TODO: checks and cleanup of ESF (see papers)
    # calculate TTF from ESF
    frq, ttf, lsf = esf2ttf(esf, bin_width)
    f10 = find_x_of_threshold(frq, ttf, 0.1)
    f50 = find_x_of_threshold(frq, ttf, 0.5)
    return frq, ttf, {'bkg': bkg, 'fgd': fgd, 'cnt': cnt, 'noi': noi, 'cnr': cnr,
                      'esf': esf, 'lsf': lsf, 'f10': f10, 'f50': f50}


def ttf_properties(dicom_images, roi_series, pixel_size, average_images=False):
    if not isinstance(dicom_images, list):
        dicom_images = [dicom_images]
    images = []
    for image in dicom_images:
        images.append(image['pixels'])
    if average_images:
        images = [np.mean(images, axis=0)]
    try:
        pixel_size_x = pixel_size[0]
        pixel_size_y = pixel_size[1]
    except TypeError:
        pixel_size_x = pixel_size
        pixel_size_y = pixel_size
    # loop over ROIs and images
    ret = []
    for i_roi, roi in enumerate(roi_series):
        # (!) in "numpy images" the 1st coordinate is y
        fgd_list = []
        bkg_list = []
        cnt_list = []
        cnr_list = []
        noi_list = []
        # TODO: average the TTFs or do the TTF on the averaged image?
        for i_image, image in enumerate(images):
            # re-estimate center (precision needed for radial profile calculation)
            roi.refine_center(image)
            frq, ttf, other = calculate_image_ttf(image, roi, pixel_size_x)
            plt.plot(frq, ttf)
            plt.xlim([0, 1.2])
            plt.ylim([0, 1.1])
            # plt.show()
            fgd_list.append(other['fgd'])
            bkg_list.append(other['bkg'])
            cnt_list.append(other['cnt'])
            cnr_list.append(other['cnr'])
            noi_list.append(other['noi'])
        print('BKG:', np.mean(bkg_list),
              'FGD:', np.mean(fgd_list),
              'CNT:', np.mean(cnt_list),
              'NOI:', np.mean(noi_list),
              'CNR:', np.mean(cnr_list))
        ret.append({
            'esf': other['esf'],
            'lsf': other['lsf'],
            'ttf': ttf,
            'frq': frq,
            'f10': other['f10'],
            'f50': other['f50'],
            'contrast': other['cnt']
        })
    return ret
