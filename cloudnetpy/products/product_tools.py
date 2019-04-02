"""General helper functions for all products."""
import numpy as np
import numpy.ma as ma
import netCDF4
from datetime import time, date, datetime
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import matplotlib.dates as mdates
import seaborn as sns
import cloudnetpy.utils as utils


def read_quality_bits(categorize_object):
    bitfield = categorize_object.getvar('quality_bits')
    keys = _get_quality_keys()
    return check_active_bits(bitfield, keys)


def read_category_bits(categorize_object):
    bitfield = categorize_object.getvar('category_bits')
    keys = _get_category_keys()
    return check_active_bits(bitfield, keys)


def check_active_bits(bitfield, keys):
    """
    Converts bitfield into dictionary.

    Args:
        bitfield (int): Array of integers containing yes/no
            information coded in the individual bits.

        keys (array_like): list of strings containing the names of the bits.
            They will be the keys in the returned dictionary.

    Returns:
        dict: Individual bits in a dictionary (with proper names).

    """
    bits = {}
    for i, key in enumerate(keys):
        bits[key] = utils.isbit(bitfield, i)
    return bits


def _get_category_keys():
    """Returns names of the 'category_bits' bits."""
    return ('droplet', 'falling', 'cold',
            'melting', 'aerosol', 'insect')


def _get_quality_keys():
    """Returns names of the 'quality_bits' bits."""
    return ('radar', 'lidar', 'clutter', 'molecular',
            'attenuated', 'corrected')


def get_source(data_handler):
    """Returns uuid (or filename if uuid not found) of the source file."""
    return getattr(data_handler.dataset, 'file_uuid', data_handler.filename)


# Tools for plotting
def convert_dtime_to_datetime(case_date, time_array):
    """Converts decimal time array to datetime array"""
    time_array = [time(int(time_array[i]), int((time_array[i] * 60) % 60),
                       int((time_array[i] * 3600) % 60))
                  for i in range(len(time_array))]
    time_array = [datetime.combine(case_date, t) for t in time_array]
    return np.asanyarray(time_array)


def colors_to_colormap(color_l):
    """Transforms list of colors to colormap"""
    return ListedColormap(sns.color_palette(color_l).as_hex())


def read_variables_and_date(field_names, nc_file):
    """Read variables from generated product file data_name: name of wanted product
    """
    data_out = []
    for name in field_names:
        data_field = netCDF4.Dataset(nc_file).variables[name][:]
        data_out.append(data_field)
    time_array = netCDF4.Dataset(nc_file).variables['time'][:]
    height = netCDF4.Dataset(nc_file).variables['height'][:] / 1000
    case_date = date(int(netCDF4.Dataset(nc_file).year),
                     int(netCDF4.Dataset(nc_file).month),
                     int(netCDF4.Dataset(nc_file).day))
    return data_out, time_array, height, case_date


def initialize_time_height_axes(ax, n, i):
    xlabel = 'Time ' + r'(UTC)'
    ylabel = 'Height ' + '$(km)$'

    date_format = mdates.DateFormatter('%H:%M')
    ax.xaxis.set_major_formatter(date_format)
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=4))
    ax.tick_params(axis='x', labelsize=12)
    #TODO: Voi varmaan tehdä ilman apumuuttujia
    if i == n-1:
        ax.set_xlabel(xlabel, fontsize=13)

    ax.tick_params(axis='y', labelsize=12)
    ax.set_ylim(0, 3)
    ax.set_ylabel(ylabel, fontsize=13)

    return ax


def generate_log_cbar_ticklabel_list(vmin, vmax):
    """Create list of log format colorbar labelticks as string"""
    log_string = []
    n = int(abs(vmin - vmax) + 1)

    for i in range(n):
        log = ('10$^{%s}$' % (int(vmin) + i))
        log_string.append(log)
        vmin = + 1

    return log_string


def initialize_figure(n):
    """ Usage is to create figure suitable different situations"""
    fig, ax = plt.subplots(n, 1, figsize=(16, 4+(n-1)*4.8))
    if n == 1:
        ax = [ax]
    return fig, ax


def interpolate_data_and_dimensions(data, times, height, new_time, new_height):
    n = np.min(data)
    data = np.asarray(data)
    data = utils.interpolate_2d(times, height, data, new_time, new_height)
    # TODO: interplotaatio ei toimi maskatuille, hoidetaan jossain vaiheessa
    data = ma.masked_where(data < n, data)
    return data


def calculate_relative_error(old_data, new_data):
    ind = np.where((old_data > 0) & (new_data > 0))
    inds = np.full(new_data.shape, False, dtype=bool)
    inds[ind] = True

    old_data[~inds] = ma.masked
    new_data[~inds] = ma.masked

    error = ((new_data - old_data) / old_data) * 100
    return error


def convert_int2decimal(x):
    return round(float(str(x) + ".0" + str(x + 1)), 2)
