import numpy as np
from numpy.testing import assert_array_equal
import pytest
from cloudnetpy.categorize import melting


@pytest.mark.parametrize("model, result", [
    ('some_ecmwf_model', (-4, 3)),
    ('some_other_model', (-8, 6)),
])
def test_find_model_temperature_range(model, result):
    assert melting._find_model_temperature_range(model) == result


@pytest.mark.parametrize("t_prof, t_range, result", [
    (np.array([300, 290, 280, 270, 260, 250, 240]), (-10, 10), [2, 3]),
    (np.array([300, 290, 280, 270, 260, 250, 240]), (-5, 5), [3]),
    (np.array([290, 280, 270, 275, 260, 250, 240]), (-10, 10), [1, 2, 3]),
    (np.array([270, 275, 260, 250, 240]), (-10, 10), [0, 1]),
    (np.array([220, 210, 200]), (-10, 10), [0]),
])
def test_get_temp_indices(t_prof, t_range, result):
    indices = melting._get_temp_indices(t_prof, t_range)
    assert_array_equal(indices, result)


@pytest.mark.parametrize("ldr, v, indices, result", [
    ([0, 1, 20, 100, 30, 2, 1], [-1, -2, -4, -1, 0, 0, 0], (1, 3, 6), True)
])
def test__is_good_ldr_peak(ldr, v, indices, result):
    assert melting._is_good_ldr_peak(ldr, v, indices) is result


@pytest.mark.parametrize("v, indices, result", [
    ([-1, -2.1, -1, 0], (1, 2), True),
    ([-1, -1.9, -1, 0], (1, 2), False),
])
def test__is_good_ldr_peak(v, indices, result):
    assert melting._is_good_v_peak(v, indices) is result
