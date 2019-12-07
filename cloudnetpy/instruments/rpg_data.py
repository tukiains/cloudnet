"""Module aiming to implement a generic RPG data reader."""
import bisect
from collections import namedtuple
import numpy as np
from cloudnetpy.instruments.rpg_header import read_rpg_header, get_rpg_file_type
import sys


class RpgBin:
    """RPG Cloud Radar Level 0/1 Version 2/3 data reader."""
    def __init__(self, filename):
        self.filename = filename
        self.header, self._file_position = read_rpg_header(filename)
        self.level, self.version = get_rpg_file_type(self.header)
        self.data = self.read_rpg_data()

    def read_rpg_data(self):
        """Reads the actual data from rpg binary file."""

        def _create_dimensions():
            """Returns possible lengths of the data arrays."""
            Dimensions = namedtuple('Dimensions', ['n_samples',
                                                   'n_gates',
                                                   'n_layers_t',
                                                   'n_layers_h'])
            return Dimensions(int(np.fromfile(file, np.int32, 1)),
                              int(self.header['n_range_levels']),
                              int(self.header['n_temperature_levels']),
                              int(self.header['n_humidity_levels']))

        def _create_variables():
            """Initializes dictionaries for data arrays."""
            vrs = {'sample_length': np.zeros(dims.n_samples, np.int),
                   'time': np.zeros(dims.n_samples, np.int),
                   'time_ms': np.zeros(dims.n_samples, np.int),
                   'quality_flag': np.zeros(dims.n_samples, np.int)}

            block1_vars = dict.fromkeys((
                'rain_rate',
                'relative_humidity',
                'temperature',
                'pressure',
                'wind_speed',
                'wind_direction',
                'voltage',
                'brightness_temperature',
                'lwp',
                'if_power',
                'elevation',
                'azimuth',
                'status_flag',
                'transmitted_power',
                'transmitter_temperature',
                'receiver_temperature',
                'pc_temperature'))

            if self.level == 1:

                block2_vars = dict.fromkeys((
                    'Ze',
                    'v',
                    'width',
                    'skewness',
                    'kurtosis'))

                if self.header['dual_polarization'] > 0:
                    block2_vars.update(dict.fromkeys((
                        'ldr',
                        'correlation_coefficient',
                        'differential_phase')))

                if self.header['dual_polarization'] == 2:
                    block2_vars.update(dict.fromkeys((
                        'slanted_Ze',
                        'slanted_ldr',
                        'slanted_correlation_coefficient',
                        'specific_differential_phase_shift',
                        'differential_attenuation')))

            else:

                block2_vars = {}

                if self.header['compression'] == 0:

                    block2_vars['doppler_spectrum'] = None

                    if self.header['dual_polarization'] > 0:
                        block2_vars.update(dict.fromkeys((
                            'doppler_spectrum_h',
                            'covariance_spectrum_re',
                            'covariance_spectrum_im')))

                else:

                    block2_vars.update(dict.fromkeys(
                        'doppler_spectrum_compressed'))

                    if self.header['dual_polarization'] > 0:
                        block2_vars.update(dict.fromkeys((
                            'doppler_spectrum_h_compressed',
                            'covariance_spectrum_re_compressed',
                            'covariance_spectrum_im_compressed')))

                if self.header['compression'] == 2:

                    block2_vars.update(dict.fromkeys((
                        'differential_reflectivity_compressed',
                        'spectral_correlation_coefficient_compressed',
                        'spectral_differential_phase_compressed')))

                    if self.header['dual_polarization'] == 2:
                        block2_vars.update(dict.fromkeys((
                            'spectral_slanted_ldr_compressed',
                            'spectral_slanted_correlation_coefficient_compressed')))

            return vrs, block1_vars, block2_vars

        def _get_float_block_lengths():
            block_one_length = (len(block1) + 3 + dims.n_layers_t +
                                (2*dims.n_layers_h) + (2*dims.n_gates))
            if self.level == 0 and self.header['dual_polarization'] > 0:
                block_one_length += 2*dims.n_gates
            return block_one_length, len(block2)

        def _init_float_blocks():
            block_one = np.zeros((dims.n_samples, n_floats1))
            if self.level == 1:
                block_two = np.zeros((dims.n_samples, dims.n_gates, n_floats2))
            else:
                max_len = max(self.header['n_spectral_samples']) * len(block2)
                block_two = np.zeros((dims.n_samples, dims.n_gates, max_len))
            return block_one, block_two

        file = open(self.filename, 'rb')
        file.seek(self._file_position)
        dims = _create_dimensions()
        aux, block1, block2 = _create_variables()
        n_floats1, n_floats2 = _get_float_block_lengths()
        float_block1, float_block2 = _init_float_blocks()

        n_samples_at_each_height = _get_n_samples(self.header)

        for sample in range(dims.n_samples):

            aux['sample_length'][sample] = np.fromfile(file, np.int32, 1)
            aux['time'][sample] = np.fromfile(file, np.uint32, 1)
            aux['time_ms'][sample] = np.fromfile(file, np.int32, 1)
            aux['quality_flag'][sample] = np.fromfile(file, np.int8, 1)
            float_block1[sample, :] = np.fromfile(file, np.float32, n_floats1)
            is_data_ind = np.where(np.fromfile(file, np.int8, dims.n_gates))[0]

            if self.level == 1:

                n_valid = len(is_data_ind)
                values = np.fromfile(file, np.float32, n_floats2 * n_valid)
                float_block2[sample, is_data_ind, :] = values.reshape(n_valid, n_floats2)

            elif self.header['compression'] == 0:

                n_var = len(block2)
                n_samples = n_samples_at_each_height[is_data_ind]
                dtype = ' '.join([f"int32, ({n_var*x},)float32, " for x in n_samples])
                data = np.array(np.fromfile(file, np.dtype(dtype), 1)[0].tolist())[1::2]
                for alt_ind, prof in zip(is_data_ind, data):
                    float_block2[sample, alt_ind, :n_samples_at_each_height[alt_ind]] = prof

            else:

                for _ in is_data_ind:

                    n_bytes_in_block = np.fromfile(file, np.int32, 1)
                    n_blocks = int(np.fromfile(file, np.int8, 1)[0])
                    min_ind, max_ind = np.fromfile(file, np.dtype(f"({n_blocks}, )int16"), 2)
                    n_indices = max_ind - min_ind

                    n_values = (sum(n_indices) + len(n_indices)) * 4 + 2
                    all_data = np.fromfile(file, np.float32, n_values)

                    if self.header['anti_alias'] == 1:
                        is_anti_applied, min_velocity = np.fromfile(file, np.dtype('int8, float32'), 1)[0]

        file.close()

        for n, name in enumerate(block1):
            block1[name] = float_block1[:, n]

        if self.level == 1:
            for n, name in enumerate(block2):
                block2[name] = float_block2[:, :, n]

        elif self.header['compression'] == 0:

            n_var = len(block2)
            for key in block2:
                block2[key] = np.zeros((dims.n_samples, dims.n_gates,
                                        max(self.header['n_spectral_samples'])))

            for n_spec in np.unique(self.header['n_spectral_samples']):
                ind = np.where(n_samples_at_each_height == n_spec)[0]
                blocks = np.split(float_block2[:, ind, :n_spec*n_var], n_var)
                for name, block in zip(block2, blocks):
                    block2[name][:, ind, :n_spec] = block

        return {**aux, **block1, **block2}


def _get_n_samples(header):
    """Finds number of spectral samples at each height."""
    array = np.ones(header['n_range_levels'], dtype=int)
    sub_arrays = np.split(array, header['chirp_start_indices'][1:])
    sub_arrays *= header['n_spectral_samples']
    return np.concatenate(sub_arrays)
