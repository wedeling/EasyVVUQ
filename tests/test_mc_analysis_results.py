import os
import easyvvuq as uq
import numpy as np
import chaospy as cp
import pytest
import logging
import pandas as pd
import json
from tests.sc.sobol_model import sobol_g_func
from easyvvuq.analysis.qmc_analysis import QMCAnalysisResults


def exact_sobols_g_func(d=2, a=[0.0, 0.5, 3.0, 9.0, 99.0]):
    # for the Sobol g function, the exact (1st-order)
    # Sobol indices are known analytically
    V_i = np.zeros(d)
    for i in range(d):
        V_i[i] = 1.0 / (3.0 * (1 + a[i])**2)
    V = np.prod(1 + V_i) - 1
    logging.debug('Exact 1st-order Sobol indices: ', V_i / V)
    return V_i / V


@pytest.fixture
def data():
    # fix random seed to make this test deterministic
    np.random.seed(10000000)
    # Create the sampler
    vary = {
        "x1": cp.Uniform(0.0, 1.0),
        "x2": cp.Uniform(0.0, 1.0)
    }
    sampler = uq.sampling.MCSampler(vary, n_mc_samples=100)
    data = {('run_id', 0): [], ('x1', 0): [], ('x2', 0): [], ('f', 0): []}
    for run_id, sample in enumerate(sampler):
        data[('run_id', 0)].append(run_id)
        data[('x1', 0)].append(sample['x1'])
        data[('x2', 0)].append(sample['x2'])
        data[('f', 0)].append(sobol_g_func([sample['x1'], sample['x2']], d=2))
    df = pd.DataFrame(data)
    return sampler, df


@pytest.fixture
def results(data):
    # Post-processing analysis
    mc_sampler, df = data
    analysis = uq.analysis.QMCAnalysis(sampler=mc_sampler, qoi_cols=['f'])
    results = analysis.analyse(df)
    return results


def test_results(results):
    assert(isinstance(results, QMCAnalysisResults))
    sobols_first_x1 = results._get_sobols_first('f', 'x1')
    sobols_first_x2 = results._get_sobols_first('f', 'x2')
    sobols_total_x1 = results._get_sobols_total('f', 'x1')
    sobols_total_x2 = results._get_sobols_total('f', 'x2')
    assert(sobols_first_x1 == pytest.approx(0.55690589, 0.001))
    assert(sobols_first_x2 == pytest.approx(0.20727553, 0.001))
    assert(sobols_total_x1 == pytest.approx(0.81327937, 0.001))
    assert(sobols_total_x2 == pytest.approx(0.38049629, 0.001))


def test_results_conf(results):
    sobols_first_x1_conf = results._get_sobols_first_conf('f', 'x1')
    assert(sobols_first_x1_conf[0] == pytest.approx(0.14387, 0.001))
    assert(sobols_first_x1_conf[1] == pytest.approx(0.894288, 0.001))
    sobols_first_x2_conf = results._get_sobols_first_conf('f', 'x2')
    assert(sobols_first_x2_conf[0] == pytest.approx(-0.110633, 0.001))
    assert(sobols_first_x2_conf[1] == pytest.approx(0.467528, 0.001))
    sobols_total_x1_conf = results._get_sobols_total_conf('f', 'x1')
    assert(sobols_total_x1_conf[0] == pytest.approx(0.613689, 0.001))
    assert(sobols_total_x1_conf[1] == pytest.approx(1.018587, 0.001))
    sobols_total_x2_conf = results._get_sobols_total_conf('f', 'x2')
    assert(sobols_total_x2_conf[0] == pytest.approx(0.243612, 0.001))
    assert(sobols_total_x2_conf[1] == pytest.approx(0.492141, 0.001))


def test_full_results(results):
    assert(results.sobols_first() == {'f': {'x1': 0.5569058947880715, 'x2': 0.20727553481694053}})
    assert(results.sobols_total() == {'f': {'x1': 0.8132793654841785, 'x2': 0.3804962894947435}})
