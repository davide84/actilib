import math
import numpy as np

from actilib.helpers.math import cart2pol, pol2cart, deg_from_rad
from actilib.helpers.geometry import find_phantom_center_and_radius, find_circles
from actilib.helpers.display import *


def is_section_diameter(diameter_mm):
    """
    Check if the provided diameter corresponds to one of the 5 measurement sections
    :param diameter_mm: the diameter as measured e.g. from an image [mm]
    :return: True if the diameter is compatible with that of a measurement section
    """
    for d in [160, 210, 260, 310, 360]:
        if math.isclose(diameter_mm, d, abs_tol=3):
            return True
    return False


def find_inserts(image, phantom_center_px, radius_factor_mm, expected_hu, tolerance_hu=100):
    expected_radius_px = int(13 / radius_factor_mm)
    expected_dfc = int(45 / radius_factor_mm)  # distance from center
    pixels = image['pixels'].copy()
    pixels[pixels < expected_hu - tolerance_hu] = expected_hu - tolerance_hu
    pixels[pixels > expected_hu + tolerance_hu] = expected_hu + tolerance_hu
    found_circles = find_circles(pixels, expected_radius_px, tolerance_px=1)
    dfc_tol_px = 3
    return_circles = []
    for circle in found_circles:
        dfc = ((circle[0]-phantom_center_px[0])**2 + (circle[1]-phantom_center_px[1])**2)**0.5
        if expected_dfc - dfc_tol_px < dfc < expected_dfc + dfc_tol_px:
            return_circles.append(circle)
    if len(return_circles) == 0:
        return None
    return return_circles


def calculate_intermediate_insert(insertA, insertB, center_xy):
    thetaA, rhoA = cart2pol(insertA[0] - center_xy[0], insertA[1] - center_xy[1])
    thetaB, rhoB = cart2pol(insertB[0] - center_xy[0], insertB[1] - center_xy[1])
    theta_step = 0.4 * math.pi  # 1/5 of full circle is the angular spacing between inserts
    if thetaA < 0:
        thetaA = 2 * math.pi + thetaA
    if thetaB < 0:
        thetaB = 2 * math.pi + thetaB
    if math.isclose(thetaA + 2 * theta_step, thetaB, abs_tol=0.1):
        thetaI = thetaA + theta_step
    else:
        thetaI = thetaA - theta_step
    if thetaI > math.pi:
        thetaI = thetaI - 2 * math.pi
    x, y = pol2cart(thetaI, rhoA/2 + rhoB/2)
    r = insertA[2]/2 + insertB[2]/2
    return [x + center_xy[0], y + center_xy[1], r]


def section_has_inserts(image, center_xy=None):
    print('----------------------------')
    if center_xy is None:
        center_xy, _, _, _ = find_phantom_center_and_radius(image)
    pixel_size_xy_mm = image['header'].PixelSpacing
    radius_factor_mm = ((pixel_size_xy_mm[0] ** 2 + pixel_size_xy_mm[1] ** 2) / 2) ** 0.5
    # windowing on bone
    ins_bone = find_inserts(image, center_xy, radius_factor_mm, 400)  # bone insert
    ins_b_na = find_inserts(image, center_xy, radius_factor_mm, 150)  # bone insert + iodine
    ins_air = find_inserts(image, center_xy, radius_factor_mm, -250)  # air insert
    # first esclusion rule: not enough clear inserts found
    if not ins_bone or not ins_b_na or not ins_air or len(ins_bone) != 1 or len(ins_b_na) != 2 or len(ins_air) != 1:
        return False
    # now we calculate the positions of the other three and we check if they are distinguishable from background
    ins_coords = {
        'bone': ins_bone[0],
        'air': ins_air[0]
    }
    for insert in ins_b_na:
        if math.isclose(ins_b_na[0][0], ins_coords['bone'][0], abs_tol=3) \
                and math.isclose(ins_b_na[0][1], ins_coords['bone'][1], abs_tol=3):
            ins_coords['iodine'] = ins_b_na[1]
        else:
            ins_coords['iodine'] = ins_b_na[0]
    # use polar coordinates to determine position of the other inserts
    # note that y coordinate goes from top to bottom: theta = 0 is at 3 o' clock and grows clockwise
    ins_coords['polystyrene'] = calculate_intermediate_insert(ins_b_na[0], ins_b_na[1], center_xy)
    ins_coords['water'] = calculate_intermediate_insert(ins_bone[0], ins_air[0], center_xy)
    # are the two low contrast inserts visible?
    from actilib.helpers.rois import PixelROI
    # reference ROI for background
    ref_ins = np.average([ins_coords['air'], ins_coords['water']], axis=0)
    ref_roi = PixelROI(ref_ins[0], ref_ins[1], ref_ins[2], shape='circular')
    ref_mean = ref_roi.get_mask_mean(image['pixels'])
    for name, ins in ins_coords.items():
        roi = PixelROI(ins[0], ins[1], ins[2], shape='circular')
        mean = roi.get_mask_mean(image['pixels'])
        if math.isclose(mean, ref_mean, abs_tol=30):
            print('Insert {} not clearly visible (HU contrast: {})'.format(name, int(ref_mean - mean)))
            return False
    return True


def section_is_uniform(image, cxy, cr):
    # print('-------------------------------')
    cix = int(cxy[0])  # index of center pixel, x coordinate
    ciy = int(cxy[1])  # index of center pixel, y coordinate
    size = int(0.7 * cr)
    submatrix = image['pixels'][ciy - size:ciy + size, cix - size:cix + size]
    '''
    quadrants = [image['pixels'][ciy - size:ciy, cix:cix + size],
                 image['pixels'][ciy:ciy + size, cix:cix + size],
                 image['pixels'][ciy - size:ciy, cix - size:cix],
                 image['pixels'][ciy - size:ciy, cix - size:cix]]
    q_means = [np.mean(q) for q in quadrants]
    std = np.std(q_means)
    print(std)
    if std > 4:  # inhomogeneities between areas
        return False
    std = np.std(submatrix)
    print(std)
    if std > 20:  # too much inhomogeneities in the section
        return False
    '''
    ptp = np.ptp(submatrix.flatten())
    # print(ptp)
    if ptp > 185:  # range too big
        return False
    mean = np.mean(submatrix)
    # print(mean)
    if not (-125 < mean < -25):  # expected HU of background is -75
        return False
    return True


def classify_slices(images):
    """
    Classify the images assuming that they describe the scan of a Mercury Phantom v. 4.0
    :param images: a list of images, each one corresponding to a DICOM pixel_array
    :return: a list of flags with image classification: 'N' = Noise, 'T' = TTF and 'x' = none of them
    """
    flags = ['x'] * len(images)
    for i, image in enumerate(images):
        cxy, r, cxy_mm, r_mm = find_phantom_center_and_radius(image)
        # print(cxy, r, cxy_mm, r_mm)
        # most restrictive condition: we must be in one of the 5 regions of fixed diameter (16/21/26/31/36 cm)
        if not is_section_diameter(r_mm * 2):
            continue  # default flag is 'x'
        # TTF - second most restrictive condition
        if section_has_inserts(image, cxy):
            flags[i] = 'T'
            continue
        # NPS - region must be uniform
        if section_is_uniform(image, cxy, r):
            flags[i] = 'N'
            continue
    return flags




