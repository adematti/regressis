#!/usr/bin/env python
# coding: utf-8

import os
import sys
import logging

import numpy as np
import pandas as pd
import healpy as hp

from regressis import DR9Footprint, setup_logging
from regressis.utils import read_fits_to_pandas, build_healpix_map


logger = logging.getLogger('Collect_desi_target')


def _redshift_selection(tracer):
    """ It gives the correct redshift range for clustering analysis as a function of tracer.  
        see: https://github.com/desihub/LSS/blob/692e1943cc87fa52490eed2181e0ca52603974f4/scripts/main/mkCat_main.py#L239 """
    if tracer == 'BGS':
        z_lim = (0.1, 0.5)
    elif tracer == 'LRG':
        z_lim = (0.4, 1.1)
    elif tracer == 'ELG' or tracer == 'ELGnoQSO':
        z_lim = (0.8, 1.5)
    elif tracer == 'QSO':
        z_lim = (0.8, 3.5)
    else:
        z_lim = (0.1, 5.9)
    return z_lim


def save_desi_data(LSS, version, tracer, nside, dir_out):
    """
    
    From clustering and randoms catalog build and save the healpix distribution of considered observed objects and the corresponding fracarea. 
    
    Parameters
    ----------
    LSS : str
        Path to locate where are the catalogs of galaxies / quasars.
    version : str
        Which version is used. Only relevant for the filename of the outputs. DA02 is expected here.
    tracer : str
        Which tracer is used. BGS_ANY / LRG / ELG / QSO.
    nside : int
        Resolution of the healpix distribution map of the objects.
    dir_out : str
        Path where the ouputs will be saved.
    """
    logger.info(f"Collect DA02 data for {tracer}:")

    data = read_fits_to_pandas(os.path.join(LSS, f'{tracer}zdone_clustering.dat.fits'))
    z_lim = _redshift_selection(tracer)
    data = data[(data['Z'] > z_lim[0]) & (data['Z'] < z_lim[1])]
    map_data = build_healpix_map(nside, data['RA'].values, data['DEC'].values, weights=data['WEIGHT_COMP'].values, in_deg2=False)

    #load photometric regions:
    north, south, des = DR9Footprint(nside, mask_lmc=False, clear_south=True, mask_around_des=True, cut_desi=False).get_imaging_surveys()
    logger.info("Number of pixels observed in each region:")
    logger.info(f"        * North: {np.sum(map_data[north] > 0)} ({np.sum(map_data[north] > 0)/np.sum(map_data > 0):2.2%})")
    logger.info(f"        * South: {np.sum(map_data[south] > 0)} ({np.sum(map_data[south] > 0)/np.sum(map_data > 0):2.2%})")
    logger.info(f"        * Des:   {np.sum(map_data[des] > 0)}  ({np.sum(map_data[des] > 0)/np.sum(map_data > 0):2.2%})")

    randoms = pd.concat([read_fits_to_pandas(os.path.join(LSS, f'{tracer}zdone_{i}_clustering.ran.fits'), columns=['RA', 'DEC', 'Z']) for i in range(10)], ignore_index=True)
    # load in deg2 since we know the density of generated randoms in deg2
    map_randoms = build_healpix_map(nside, randoms['RA'].values, randoms['DEC'].values, in_deg2=True)
    # a random file is 2500 randoms per deg2
    mean = 10*2500
    #TO DO IN THE NEXT: or divide by the correct value in each pixel ! /global/cfs/cdirs/desi/target/catalogs/dr9/0.49.0/randoms/resolve/randoms-1-0.fits
    fracarea = map_randoms / mean
    fracarea[fracarea == 0] = np.NaN
    # remove pixels with too small fracarea
    sel = 1/fracarea > 5.0
    fracarea[sel] = np.NaN
    logger.info(f"{np.sum(sel)} pixels are outlier on {np.sum(fracarea>0)}")

    ## savedata (without fracarea and not in degree !! --> we want just the number of object per pixel):
    filename_data = os.path.join(dir_out, f'{version}_{tracer}_{nside}.npy')
    logger.info(f'Save data: {filename_data}')
    np.save(filename_data, map_data)
    filename_fracarea = os.path.join(dir_out, f'{version}_{tracer}_fracarea_{nside}.npy')
    logger.info(f'Save corresponding fracarea: {filename_fracarea}\n')
    np.save(filename_fracarea, fracarea)


if __name__ == '__main__':

    setup_logging()

    # Wiki page for DA02: https://desi.lbl.gov/trac/wiki/ClusteringWG/LSScat/DA02main/version1
    # We compte photometric weight for clustering catalog.
    
    # The offical repos for DA02 is not updated with the last version of LSS code for the moment
    # I'm still using everest/test version (the number of targets will not be changed since we are in evererst 
    # But take care the repo can be broken at any moment...
    
    LSS = '/global/cfs/cdirs/desi/survey/catalogs/main/LSS/everest/LSScats/test'
    #LSS = '/global/cfs/cdirs/desi/survey/catalogs/DA02/LSS/everest/LSScats/1'

    version = 'DA02'
    tracers = ['BGS_ANY', 'LRG', 'ELG', 'QSO']
    nside = 128 # same nside for all tracer
    dir_out = os.path.join(os.path.abspath(os.path.dirname(__file__)), '../data/')

    for tracer in tracers:
        save_desi_data(LSS, version, tracer, nside, dir_out)
