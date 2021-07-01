import pkgutil
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import math
import tempfile
import json
import os.path as path
from datetime import datetime
from fpdf import FPDF
from tabulate import tabulate


def trunc_dec(number, num_dec):
    return int(number * 10**num_dec) / 10**num_dec


def _save_current_figure(current_plt):
    with tempfile.NamedTemporaryFile(suffix='.png') as tf:
        temp_file_name = tf.name
    current_plt.savefig(temp_file_name, format='png')
    return temp_file_name


def _plot_patches(ax, z, values, color):
    i_l = 0
    for f, flag in enumerate(values):
        if flag and i_l == 0:  # a section begins
            i_l = f
        if not flag and i_l > 0:  # a section has ended
            ax.add_patch(patches.Rectangle((z[f], 0), f - i_l, ax.get_ylim()[1], ec=color, fc=color, alpha=0.2))
            i_l = 0


def plot_current_profile(full_data):
    plt.clf()
    data = full_data['values_current']
    scout_image = json.loads(pkgutil.get_data(__name__, path.join('../resources', 'scout_image.json')).decode("utf-8"))
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
    return _save_current_figure(plt)


def plot_nps(full_data):
    plt.clf()
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
    plt.gcf().set_size_inches(4, 4)
    return _save_current_figure(plt)


def plot_normalized_nps(full_data):
    plt.clf()
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
    plt.gcf().set_size_inches(4, 4)
    return _save_current_figure(plt)


def plot_2d_nps(full_data):
    plt.clf()
    data_nps = full_data['values_nps']
    data_freq = full_data['values_freq']
    fig, axs = plt.subplots(nrows=1, ncols=len(data_nps))
    fig.set_size_inches(10, 2)
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
    return _save_current_figure(plt)


def get_nps_table(full_data):
    data = full_data['values_nps']
    table_data = []
    for key, val in data.items():
        table_data.append([key[1:-2], val['noise'], val['fpeak'], val['fav']])
    return table_data


def print_nps_table(full_data):
    table_data = get_nps_table(full_data)
    print(tabulate(table_data, headers=['Diameter [mm]', 'Noise [HU]', 'fpeak [1/mm]', 'fav [1/mm]']))


def plot_ttf(full_data):
    plt.clf()
    data = full_data['values_ttf']
    nrows = len(data)
    ncols = len(data[list(data.keys())[0]])
    fig, axs = plt.subplots(nrows=nrows, ncols=ncols)
    fig.set_size_inches(10, 10)
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
    return _save_current_figure(plt)


def get_ttf_table(full_data):
    table_data = []
    for insert in full_data['values_ttf']:
        for diameter in full_data['values_ttf'][insert]:
            data = full_data['values_ttf'][insert][diameter]
            table_data.append([insert, diameter[1:-2] + ' mm',
                               data['contrast'], data['f10'], data['f50']])
    return table_data


def print_ttf_table(full_data):
    table_data = get_ttf_table(full_data)
    print(tabulate(table_data, headers=['Insert', 'Diameter [mm]', 'Contrast [HU]', 'f10 [1/mm]', 'f50 [1/mm]']))


def plot_dprime_vs_size(full_data):
    plt.clf()
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
    return _save_current_figure(plt)


def get_dprime_table(full_data):
    data = full_data['values_dprime']
    table_data = []
    for key, val in data.items():
        table_data.append([key, val['alpha'], val['beta'], val['residual']] + list(val['dprimes'].values()))
    return table_data


def print_dprime_table(full_data):
    table_data = get_dprime_table(full_data)
    print(tabulate(table_data, headers=['Insert', 'a', 'b', 'residual',
                                        'd\' (160)', 'd\' (210)', 'd\' (260)', 'd\' (310)', 'd\' (360)']))


#
# PDF report generation
#
def _store_current_font(pdf_doc):
    return {
        'family': pdf_doc.font_family,
        'style': pdf_doc.font_style,
        'size': pdf_doc.font_size
    }


def _restore_saved_font(pdf_doc, saved_font):
    pdf_doc.set_font(saved_font['family'], saved_font['style'], saved_font['size'])


def _add_horizontal_line(pdf_doc, margin_before=4, margin_after=4):
    pdf_doc.line(10, pdf_doc.get_y() + margin_before, 200, pdf_doc.get_y() + margin_before)
    pdf_doc.set_y(pdf_doc.get_y() + margin_before + margin_after)


def _add_section(pdf_doc, section_title):
    cf = _store_current_font(pdf_doc)
    pdf_doc.set_font('arial', 'B', 14)
    pdf_doc.set_text_color(0, 128, 255)
    pdf_doc.cell(0, 7, section_title, 0, 2, 'L')
    pdf_doc.set_text_color(0, 0, 0)
    _restore_saved_font(pdf_doc, cf)
    _add_horizontal_line(pdf_doc, 0)


def generate_report(data):
    pdf = FPDF()

    # title
    pdf.add_page()
    pdf.set_font('arial', 'B', 20)
    pdf.cell(10, pdf.font_size + 2, "imQuest Mercury Phantom Report", 0, 2, 'L')
    pdf.set_font('arial', '', 10)
    pdf.cell(10, pdf.font_size + 2, "Report generated on " + datetime.now().strftime("%d-%b-%Y %H:%M"), 0, 2, 'L')
    _add_horizontal_line(pdf, 10, 10)

    # series info
    _add_section(pdf, 'Series Info')
    pdf.set_font('arial', '', 12)
    for key, value in data['info_series'].items():
        pdf.cell(50, pdf.font_size + 2, key + ':', 0, 0, 'R')
        pdf.cell(130, pdf.font_size + 2, str(value), 0, 2, 'L')
        pdf.cell(-50)

    # tube current profile
    pdf.add_page()
    _add_section(pdf, 'Tube Current Profile')
    pdf.image(plot_current_profile(data), x=0, w=200, h=150)

    # noise properties
    pdf.add_page()
    _add_section(pdf, 'Noise Properties')
    pdf.image(plot_2d_nps(data), x=0, y=20, w=200, h=40)
    y = 70
    pdf.image(plot_nps(data), x=10, y=y, w=90, h=70)
    pdf.image(plot_normalized_nps(data), x=100, y=y, w=90, h=70)

    pdf.set_font(pdf.font_family, 'B', 10)
    pdf.set_y(160)
    pdf.cell(50, pdf.font_size + 2, 'Phantom Diameter [mm]', 0, 0, 'R')
    pdf.cell(30, pdf.font_size + 2, 'Noise [HU]', 0, 0, 'R')
    pdf.cell(30, pdf.font_size + 2, 'fpeak [mm^-1]', 0, 0, 'R')
    pdf.cell(30, pdf.font_size + 2, 'fav [mm^-1]', 0, 2, 'R')
    pdf.set_font(pdf.font_family, '', 10)
    for table_row in get_nps_table(data):
        pdf.cell(-110)
        pdf.cell(50, pdf.font_size + 2, str(table_row[0]), 0, 0, 'R')
        pdf.cell(30, pdf.font_size + 2, '{:.01f}'.format(table_row[1]), 0, 0, 'R')
        pdf.cell(30, pdf.font_size + 2, '{:.02f}'.format(table_row[2]), 0, 0, 'R')
        pdf.cell(30, pdf.font_size + 2, '{:.02f}'.format(table_row[3]), 0, 2, 'R')

    # resolution (ttf) properties
    pdf.add_page()
    _add_section(pdf, 'Resolution Properties')
    pdf.image(plot_ttf(data), x=0, y=20, w=200, h=200)
    pdf.add_page()
    pdf.set_font(pdf.font_family, 'B', 10)
    pdf.cell(30, pdf.font_size + 2, 'Insert', 0, 0, 'R')
    pdf.cell(50, pdf.font_size + 2, 'Phantom Diameter [mm]', 0, 0, 'R')
    pdf.cell(30, pdf.font_size + 2, 'Contrast [HU]', 0, 0, 'R')
    pdf.cell(30, pdf.font_size + 2, 'f_10 [mm^-1]', 0, 0, 'R')
    pdf.cell(30, pdf.font_size + 2, 'f_50 [mm^-1]', 0, 2, 'R')
    pdf.set_font(pdf.font_family, '', 10)
    for table_row in get_ttf_table(data):
        pdf.cell(-140)
        pdf.cell(30, pdf.font_size + 2, table_row[0], 0, 0, 'R')
        pdf.cell(50, pdf.font_size + 2, str(table_row[1]), 0, 0, 'R')
        pdf.cell(30, pdf.font_size + 2, '{:.01f}'.format(table_row[2]), 0, 0, 'R')
        pdf.cell(30, pdf.font_size + 2, '{:.02f}'.format(table_row[3]), 0, 0, 'R')
        pdf.cell(30, pdf.font_size + 2, '{:.02f}'.format(table_row[4]), 0, 2, 'R')

    # detectability index
    pdf.add_page()
    _add_section(pdf, 'Detectability Index vs Phantom Size')
    pdf.image(plot_dprime_vs_size(data), x=0, y=20, w=200, h=150)
    pdf.set_y(180)
    pdf.set_font(pdf.font_family, 'B', 10)
    pdf.cell(25, pdf.font_size + 2, 'Insert', 0, 0, 'R')
    pdf.cell(15, pdf.font_size + 2, 'a', 0, 0, 'R')
    pdf.cell(25, pdf.font_size + 2, 'b', 0, 0, 'R')
    pdf.cell(20, pdf.font_size + 2, 'residual', 0, 0, 'R')
    pdf.cell(15, pdf.font_size + 2, 'D\'_160', 0, 0, 'R')
    pdf.cell(15, pdf.font_size + 2, 'D\'_210', 0, 0, 'R')
    pdf.cell(15, pdf.font_size + 2, 'D\'_260', 0, 0, 'R')
    pdf.cell(15, pdf.font_size + 2, 'D\'_310', 0, 0, 'R')
    pdf.cell(15, pdf.font_size + 2, 'D\'_360', 0, 2, 'R')
    pdf.set_font(pdf.font_family, '', 10)
    for table_row in get_dprime_table(data):
        pdf.cell(-145)
        pdf.cell(25, pdf.font_size + 2, table_row[0], 0, 0, 'R')
        pdf.cell(15, pdf.font_size + 2, '{:.01f}'.format(table_row[1]), 0, 0, 'R')
        pdf.cell(25, pdf.font_size + 2, '{:.03e}'.format(table_row[2]), 0, 0, 'R')
        pdf.cell(20, pdf.font_size + 2, '{:.02f}'.format(table_row[3]), 0, 0, 'R')
        pdf.cell(15, pdf.font_size + 2, '{:.01f}'.format(table_row[4]), 0, 0, 'R')
        pdf.cell(15, pdf.font_size + 2, '{:.01f}'.format(table_row[5]), 0, 0, 'R')
        pdf.cell(15, pdf.font_size + 2, '{:.01f}'.format(table_row[6]), 0, 0, 'R')
        pdf.cell(15, pdf.font_size + 2, '{:.01f}'.format(table_row[7]), 0, 0, 'R')
        pdf.cell(15, pdf.font_size + 2, '{:.01f}'.format(table_row[8]), 0, 2, 'R')

    # software info
    pdf.add_page()
    _add_section(pdf, 'imQuest Version Info')
    pdf.set_font('arial', '', 12)
    pdf.set_font(pdf.font_family, 'B', 10)
    pdf.cell(40, pdf.font_size + 2, 'Repository', 0, 0, 'R')
    pdf.cell(90, pdf.font_size + 2, 'commit', 0, 0, 'R')
    pdf.cell(20, pdf.font_size + 2, 'branch', 0, 2, 'R')
    pdf.set_font(pdf.font_family, '', 10)
    for repo in data['info_software']:
        pdf.cell(-130)
        pdf.cell(40, pdf.font_size + 2, repo['RepositoryName'], 0, 0, 'R')
        pdf.cell(90, pdf.font_size + 2, repo['GitID'], 0, 0, 'R')
        pdf.cell(20, pdf.font_size + 2, repo['BranchName'], 0, 2, 'R')

    # writeout
    pdf.output('test.pdf', 'F')
