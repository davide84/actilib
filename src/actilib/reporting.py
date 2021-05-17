import pkgutil
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import math
import json
import os.path as path
from tabulate import tabulate


def trunc_dec(number, num_dec):
    return int(number * 10**num_dec) / 10**num_dec


def plot_dprime_vs_size(full_data):
    data = full_data['values_dprime']
    plt.title('Detectability Index vs Phantom Size')
    plt.xlabel('Phantom Diameter [mm]')
    plt.ylabel('Detectability Index')
    plt.gcf().set_size_inches(8, 6)
    legend_labels = []
    x_values = {}
    for insert_key in data:
        x_values[insert_key] = []
        y_values = []
        for diameter_key in data[insert_key]['dprimes']:
            diameter_mm = int(diameter_key[1:-2])  # 'd260mm' -> 260
            x_values[insert_key].append(diameter_mm)
            y_values.append(data[insert_key]['dprimes'][diameter_key])
        plt.plot(x_values[insert_key], y_values, 'o', fillstyle='none')
        plt.xticks(x_values[insert_key])
        legend_labels.append(insert_key)
    plt.gca().set_prop_cycle(None)  # reset color cycle to have same colors for markers and fit lines
    for insert_key in data:
        y_fitted = [data[insert_key]['alpha'] * math.exp(data[insert_key]['beta'] * x) for x in x_values[insert_key]]
        plt.plot(x_values[insert_key], y_fitted, '--')
    plt.legend(legend_labels)
    plt.show()


def print_dprime_table(full_data):
    data = full_data['values_dprime']
    table_data = []
    for key, val in data.items():
        table_data.append([key, val['alpha'], val['beta'], val['residual']] + list(val['dprimes'].values()))
    print(tabulate(table_data, headers=['Insert', 'a', 'b', 'residual',
                                        'd\' (160)', 'd\' (210)', 'd\' (260)', 'd\' (310)', 'd\' (360)']))


def _plot_patches(ax, z, values, color):
    i_l = 0
    for f, flag in enumerate(values):
        if flag and i_l == 0:  # a section begins
            i_l = f
        if not flag and i_l > 0:  # a section has ended
            ax.add_patch(patches.Rectangle((z[f], 0), f - i_l, ax.get_ylim()[1], ec=color, fc=color, alpha=0.2))
            i_l = 0


def plot_current_profile(full_data):
    data = full_data['values_current']
    scout_image = json.loads(pkgutil.get_data(__name__, path.join('resources', 'scout_image.json')).decode("utf-8"))
    # plot the current
    fig, axs = plt.subplots(1, 1)
    fig.set_size_inches(8, 6)
    axs.set_xlabel('Slice Position [mm]')
    axs.set_ylim(data['ma']['limits'])
    axs.set_yticks(range(0, data['ma']['limits'][1], 5))
    axs.set_ylabel(data['ma']['label'])
    axs.plot(data['z'], data['ma']['values'], 'r')
    axs.set_zorder(1)
    axs.patch.set_visible(False)
    # plot the background image and the WED curve on the secondary axis
    sec_ymax = len(scout_image)
    secax = axs.twinx()
    secax.set_ylim([0, sec_ymax])
    secax.set_ylabel('Water Equivalent Diameter [mm]')
    secax.imshow(scout_image, cmap='gray', extent=[data['z'][-1], data['z'][0], 0, sec_ymax], aspect='auto')
    secax.plot(data['z'], data['wed'], 'b')
    # plot the locations
    _plot_patches(secax, data['z'], data['nps_slices'], 'y')
    _plot_patches(secax, data['z'], data['ttf_slices'], 'g')
    # display
    plt.show()


def plot_nps(full_data):
    phantom_info = full_data['info_phantom']
    data_nps = full_data['values_nps']
    data_freq = full_data['values_freq']
    plt.title('Noise Power Spectra')
    plt.xlabel('Spatial Frequency [mm$^{-1}$]')
    plt.ylabel('NPS [mm$^2$HU$^2$]')
    plt.xlim(right=phantom_info['nyquist_frequencies']['fy'])
    legend_labels = []
    for key, val in data_nps.items():
        plt.plot(data_freq['nps_f'], val['NPS'])
        legend_labels.append(key[1:-2] + ' mm')
    plt.legend(legend_labels)
    plt.ylim(bottom=0)
    plt.show()


def plot_normalized_nps(full_data):
    phantom_info = full_data['info_phantom']
    data_nps = full_data['values_nps']
    data_freq = full_data['values_freq']
    plt.title('Normalized Noise Power Spectra')
    plt.xlabel('Spatial Frequency [mm$^{-1}$]')
    plt.ylabel('nNPS [mm$^2$]')
    plt.xlim(right=phantom_info['nyquist_frequencies']['fy'])
    legend_labels = []
    for key, val in data_nps.items():
        norm_nps = [nps / (val['noise']**2) for nps in val['NPS']]
        plt.plot(data_freq['nps_f'], norm_nps)
        legend_labels.append(key[1:-2] + ' mm')
    plt.legend(legend_labels)
    plt.ylim(bottom=0)
    plt.show()


def plot_2d_nps(full_data):
    data_nps = full_data['values_nps']
    data_freq = full_data['values_freq']
    fig, axs = plt.subplots(nrows=1, ncols=len(data_nps))
    for d, diameter_key in enumerate(data_nps):
        nps = data_nps[diameter_key]
        # preparing the data
        num_labels = 2
        num_pixels = len(nps['NPS_2D'][0])
        step_labels = int(num_pixels / (num_labels - 1)) - 1
        pixel_range = (data_freq['nps_fx'][-1] - data_freq['nps_fx'][0]) / (num_pixels - 1)
        # image_range = [data_freq['nps_fx'][0]-0.5*pixel_range, data_freq['nps_fx'][-1]+0.5*pixel_range]  # matlab way
        image_range = [data_freq['nps_fx'][0], data_freq['nps_fx'][-1] + pixel_range]
        image_range = [trunc_dec(image_range[0], 4), trunc_dec(image_range[1], 4)]
        # plotting
        axs[d].imshow(nps['NPS_2D'], cmap='gray', vmax=np.max(nps['NPS_2D']))
        axs[d].set_title(diameter_key[1:-2] + ' mm')
        if d == 0:
            axs[d].set_xticks(range(0, num_pixels, step_labels))
            axs[d].set_xticklabels(image_range)
            axs[d].set_yticks(range(0, num_pixels, step_labels))
            axs[d].set_yticklabels(image_range)
        else:
            axs[d].set_xticks([])
            axs[d].set_yticks([])
    plt.show()


def print_nps_table(full_data):
    data = full_data['values_nps']
    table_data = []
    for key, val in data.items():
        table_data.append([key[1:-2], val['noise'], val['fpeak'], val['fav']])
    print(tabulate(table_data, headers=['Diameter [mm]', 'Noise [HU]', 'fpeak [1/mm]', 'fav [1/mm]']))


def plot_ttf(full_data):
    data = full_data['values_ttf']
    nrows = len(data)
    ncols = len(data[list(data.keys())[0]])
    fig, axs = plt.subplots(nrows=nrows, ncols=ncols)
    fig.set_size_inches(8, 6)
    for i, insert in enumerate(data.keys()):
        for d, diameter in enumerate(data[insert].keys()):
            x = full_data['values_freq']['ttf_f']
            y = data[insert][diameter]['TTF']  # notice the inverted indexes
            axs[i][d].set_xlim(0.0, 0.6)
            axs[i][d].set_xticks([0, 0.2, 0.4, 0.6])
            axs[i][d].set_ylim(0.0, 1.0)
            axs[i][d].set_yticks([0, 0.25, 0.5, 0.75, 1])
            axs[i][d].plot(x, y)
            axs[i][d].grid(True)
            if i == 0:
                axs[i][d].set_title(diameter[1:-2] + ' mm')
            if i != nrows - 1:
                axs[i][d].set_xticklabels([])
            elif d == int(nrows / 2):
                axs[i][d].set_xlabel('Spatial Frequency [mm^{-1}]')
            if d == 0:
                axs[i][d].set_ylabel(insert + '\nTTF')
            else:
                axs[i][d].set_yticklabels([])
    plt.show()


def print_ttf_table(full_data):
    table_data = []
    for insert in full_data['values_ttf']:
        for diameter in full_data['values_ttf'][insert]:
            data = full_data['values_ttf'][insert][diameter]
            table_data.append([insert, diameter[1:-2] + ' mm',
                               data['contrast'], data['f10'], data['f50']])
    print(tabulate(table_data, headers=['Insert', 'Diameter [mm]', 'Contrast [HU]', 'f10 [1/mm]', 'f50 [1/mm]']))
