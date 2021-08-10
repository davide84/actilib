import matplotlib.pyplot as plt
import numpy as np
from pydicom import dcmread
from pydicom.pixel_data_handlers.util import apply_modality_lut
from actilib.helpers.geometry import find_phantom_center_and_radius
from actilib.helpers.noise import background_properties
from actilib.helpers.rois import create_circle_of_rois


NPS_ROD_DIAMETER_MM = 15
NPS_ROI_DIAMETER_MM = 30
NPS_ROI_DISTCENT_MM = 10 + (NPS_ROD_DIAMETER_MM + NPS_ROI_DIAMETER_MM) / 2  # distance from center


if __name__ == '__main__':
    #
    # read the images
    #
    images = []
    for i in range(16):
        filename = '/home/cester/git/actilib/src/actilib/resources/dicom/nps/{:04d}_nps.dcm'.format(162-i)
        dicom_data = dcmread(filename)
        images.append(apply_modality_lut(dicom_data.pixel_array, dicom_data))
    pixel_size_xy_mm = np.array(dicom_data.PixelSpacing)
    image_size_xy_px = np.array([len(images[0]), len(images[0][0])])
    image_center_xy_px, section_radius_px = find_phantom_center_and_radius(images[0])

    #
    # create and visualize the ROIs
    #
    roi_diameter_px = NPS_ROI_DIAMETER_MM / pixel_size_xy_mm[0]
    roi_distcent_px = NPS_ROI_DISTCENT_MM / pixel_size_xy_mm[0]
    rois = create_circle_of_rois(8, roi_diameter_px, roi_distcent_px, image_center_xy_px[0], image_center_xy_px[1])

    # fig, ax = plt.subplots()
    # ax.imshow(images[0], cmap=plt.cm.bone, vmin=-255, vmax=255)
    # import matplotlib.patches as patches
    # for roi in rois:
    #     x = roi.edge_l()
    #     y = roi.edge_t()
    #     rect = patches.Rectangle((x, y), roi.size(), roi.size(), linewidth=1, edgecolor='r', facecolor='none')
    #     ax.add_patch(rect)
    # plt.show()

    #
    # loop on the ROIs, extract the pixels and calculate the ROI values
    #
    prop = background_properties(images, rois, pixel_size_xy_mm)

    # plotting
    plt.imshow(prop['nps_2d'], cmap=plt.cm.bone)
    plt.show()
    plt.plot(prop['f1d'], prop['nps_1d'])
    plt.xlim([0, 0.6])
    plt.ylim([0, 1000])
    plt.show()

