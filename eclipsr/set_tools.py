"""ECLIPSR

This module contains functions to analyse (large) sets of light curves
using parallelisation.

[note] this module is a work in progress, it is recommended to understand and
modify this code to fit your needs before using it.

Code written by: Luc IJspeert
"""

import os
import time
import functools as fct
import numpy as np
import multiprocessing as mp
import astropy.io.fits as fits

from . import eclipse_finding as ecf
from . import utility as ut


# globals
empty_result = (-1, -1, -1, False, False, 1, np.array([[-1., -1.], [-1., -1.]]), np.array([[-1., -1.], [-1., -1.]]),
                np.array([]), np.array([]), np.array([]), np.array([]), np.array([]),
                np.zeros((0, 4), dtype=np.int64), np.array([], dtype=np.int64),
                np.array([], dtype=np.int32))


def get_fits_data(file_name, index=0):
    """Returns the data from a fits file.
    Optional arg: HDUlist index.
    """
    if ((file_name[-5:] != '.fits') & (file_name[-4:] != '.fit')):
        file_name += '.fits'
    
    with fits.open(file_name, mode='readonly') as hdul:
        data = hdul[index].data
    return data


def ephem_from_file(file_name, delimiter=None):
    times, signal = np.loadtxt(file_name, delimiter=delimiter, unpack=True)
    times, signal = ut.ingest_signal(times, signal + 1, tess_sectors=False)
    try:
        result = ecf.find_eclipses(times, signal, mode=1, max_n=80, tess_sectors=False)
    except:
        print(f'an error happened in the following file: {file_name}')
        result = []
    return result


def from_file(file_name, delimiter=None, save_dir=None):
    times, signal = np.loadtxt(file_name, delimiter=delimiter, unpack=True)
    times, signal = ut.ingest_signal(times, signal + 1, tess_sectors=False)
    
    source_id = os.path.basename(file_name)
    
    try:
        result = ecf.find_eclipses(times, signal, mode=2, max_n=80, tess_sectors=False)
    except:
        print(f'an error happened in the following file: {file_name}')
        result = empty_result
    
    if save_dir is not None:
        ut.save_results(result, os.path.join(save_dir, f'{source_id}_eclipsr'), identifier=source_id)
    return result


def from_tic(tic, all_files=None, save_dir=None):
    tic_files = [file for file in all_files if f'{tic:016.0f}' in file]
    times = np.array([])
    signal = np.array([])
    qual_flags = np.array([])
    for file in tic_files:
        tess_data = get_fits_data(file, 1)
        times = np.append(times, tess_data['TIME'])
        if ('PDCSAP_FLUX' in tess_data.columns.names):
            signal = np.append(signal, tess_data['PDCSAP_FLUX'])
        elif ('KSPSAP_FLUX' in tess_data.columns.names):
            # signal = np.append(signal, tess_data['KSPSAP_FLUX'])
            # actually use the SAP for MIT-QLP data
            signal = np.append(signal, tess_data['SAP_FLUX'])
        else:
            signal = np.append(signal, tess_data['SAP_FLUX'])
        qual_flags = np.append(qual_flags, tess_data['QUALITY'])
    
    quality = (qual_flags == 0)
    times, signal = ut.ingest_signal(times, signal, tess_sectors=True, quality=quality)
    
    if (len(times) < 10):
        result = empty_result
    else:
        try:
            result = ecf.find_eclipses(times, signal, mode=2, max_n=80, tess_sectors=True)
        except:
            print(f'an error happened in the following tic: {tic}')
            result = empty_result
    
    if save_dir is not None:
        ut.save_results(result, os.path.join(save_dir, f'{tic}_eclipsr'), identifier=tic)
    return result


def analyse_set(target_list, function='ephem_from_file', n_threads=os.cpu_count()-2, **kwargs):
    """Give a set of file names or target identifiers depending on the function used.
    The eclipsr program will be run in parallel on the set.
    
    functions that can be used:
    [ephem_from_file, from_file, from_tic]
    """
    t1 = time.time()
    with mp.Pool(processes=n_threads) as pool:
        results = pool.map(fct.partial(eval(function), **kwargs), target_list)
    t2 = time.time()
    print(f'Finished analysing set in: {(t2 - t1):1.2} s ({(t2 - t1) / 3600:1.2} h) for {len(target_list)} targets,')
    print(f'using {n_threads} threads ({(t2 - t1) * n_threads / len(target_list):1.2} '
          's average per target single threaded).')
    return results
