import numpy as np
import matplotlib.pyplot as plt
from actilib.helpers.math import fft_frequencies, radial_profile, esf2ttf
from actilib.helpers.rois import get_masked_image
from actilib.helpers.display import display_image_with_rois


def ttf_properties(dicom_images, roi_series, pixel_size, fft_samples=128):
    try:
        pixel_size_x = pixel_size[0]
        pixel_size_y = pixel_size[1]
    except TypeError:
        pixel_size_x = pixel_size
        pixel_size_y = pixel_size
    # prepare variables
    fft_size = [fft_samples, fft_samples]
    freq_x = fft_frequencies(fft_samples, pixel_size_x)
    freq_y = fft_frequencies(fft_samples, pixel_size_y)
    dfreq_x = 1 / (pixel_size_x * fft_samples)
    dfreq_y = 1 / (pixel_size_y * fft_samples)

    # loop over ROIs and images
    for i_roi, roi in enumerate(roi_series):
        # (!) in "numpy images" the 1st coordinate is y
        [y1, y2, x1, x2] = roi.indexes_yx()
        fgd_list = []
        bkg_list = []
        cnr_list = []
        noi_list = []
        for i_image, image in enumerate(dicom_images):
            mask_fgd = roi.get_annular_mask(image['pixels'], margin_outer=-roi.radius() * 0.1, margin_inner=-roi.radius())
            mask_bkg = roi.get_annular_mask(image['pixels'], margin_outer=roi.radius(), margin_inner=roi.radius()*0.8)
            image_masked_fgd = get_masked_image(image['pixels'], mask_fgd)
            image_masked_bkg = get_masked_image(image['pixels'], mask_bkg)
            # display_image_with_rois(image['pixels'], roi)
            # display_image_with_rois(image_masked_fgd.filled(0), roi)
            # display_image_with_rois(image_masked_bkg.filled(0), roi)
            fgd = image_masked_fgd.mean()
            bkg = image_masked_bkg.mean()
            noi = image_masked_bkg.std()
            cnt = fgd - bkg
            cnr = abs(cnt/noi)
            print(bkg, fgd, cnt, noi, cnr)
            fgd_list.append(fgd)
            bkg_list.append(bkg)
            noi_list.append(noi)
            cnr_list.append(cnr)
            # re-estimate center (precision needed for radial profile calculation)
            # TODO
            roi_cx = roi.center_x()
            roi_cy = roi.center_y()
            roi.set_center(roi_cx, roi_cy)
            # crop image and subtract background
            img_crop = image['pixels'][roi.edge_t(roi.radius()):roi.edge_b(roi.radius()),
                                       roi.edge_l(roi.radius()):roi.edge_r(roi.radius())] - bkg
            img_radi = roi.get_distance_from_center(image['pixels'])  # needs accurate roi center
            img_radi = img_radi[roi.edge_t(roi.radius()):roi.edge_b(roi.radius()),
                                roi.edge_l(roi.radius()):roi.edge_r(roi.radius())]
            # calculate radial profile
            bin_width = pixel_size_x / 10.0  # arbitrary - the higher, the more detailed the ESF estimation
            bin_range = [0.0, 1.5 * roi.radius()]  # 1.5 > sqrt(2) to that corner pixels can be included
            distance, esf, variance = radial_profile(img_crop, img_radi, bin_range=bin_range,
                                                     bin_number=int(bin_range[1] / bin_width + 0.5))
            # TODO: checks and cleanup of ESF
            #
            # calculate TTF from ESF
            frequencies, ttf = esf2ttf(esf, bin_width)
            print(frequencies)
            plt.plot(frequencies, ttf)
            plt.xlim([0, 1.0])
            plt.show()

            return
    print('BKG:', np.mean(bkg_list),
          'FGD:', np.mean(fgd_list),
          'NOI:', np.mean(noi_list),
          'CNR:', np.mean(cnr_list))
    esf_2d = None
    # esf_freqs, esf_1d, esf_var = radial_profile(esf_2d, freq_x, freq_y)

    return {

    }
