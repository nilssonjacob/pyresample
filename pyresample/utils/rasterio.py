#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2019-2021 Pyresample developers
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Utilities for working with rasterio objects."""
import pyresample

from . import proj4_str_to_dict


def _get_area_def_from_gdal(dataset, area_id=None, description=None, proj_id=None, projection=None):
    from pyresample.future.geometry import AreaDefinition

    # a: width of a pixel
    # b: row rotation (typically zero)
    # c: x-coordinate of the upper-left corner of the upper-left pixel
    # d: column rotation (typically zero)
    # e: height of a pixel (typically negative)
    # f: y-coordinate of the of the upper-left corner of the upper-left pixel
    c, a, b, f, d, e = dataset.GetGeoTransform()
    if not (b == d == 0):
        raise ValueError('Rotated rasters are not supported at this time.')
    area_extent = (c, f + e * dataset.RasterYSize, c + a * dataset.RasterXSize, f)

    if projection is None:
        from osgeo import osr
        proj = dataset.GetProjection()
        if proj != '':
            sref = osr.SpatialReference(wkt=proj)
            projection = proj4_str_to_dict(sref.ExportToProj4())
        else:
            raise ValueError('The source raster is not gereferenced, please provide the value of proj_dict')

        if proj_id is None:
            proj_id = proj.split('"')[1]

    attrs = {"name": area_id, "description": description, "proj_id": proj_id}
    area_def = AreaDefinition(projection, dataset.RasterXSize, dataset.RasterYSize, area_extent, attrs=attrs)
    return area_def


def _get_area_def_from_rasterio(dataset, area_id, description, proj_id=None, projection=None):
    from pyresample.future.geometry import AreaDefinition

    a, b, c, d, e, f, _, _, _ = dataset.transform
    if not (b == d == 0):
        raise ValueError('Rotated rasters are not supported at this time.')

    if projection is None:
        projection = dataset.crs
        if projection is None:
            raise ValueError('The source raster is not gereferenced, please provide the value of proj_dict')

        if proj_id is None:
            proj_id = projection.wkt.split('"')[1]

    attrs = {"name": area_id, "description": description, "proj_id": proj_id}
    area_def = AreaDefinition(projection, dataset.width, dataset.height, dataset.bounds, attrs=attrs)
    return area_def


def get_area_def_from_raster(source, area_id=None, name=None, proj_id=None, projection=None):
    """Construct AreaDefinition object from raster.

    Parameters
    ----------
    source : str, Dataset, DatasetReader or DatasetWriter
        A file name. Also it can be ``osgeo.gdal.Dataset``,
        ``rasterio.io.DatasetReader`` or ``rasterio.io.DatasetWriter``
    area_id : str, optional
        ID of area
    name : str, optional
        Description of area
    proj_id : str, optional
        ID of projection
    projection : pyproj.CRS, dict, or string, optional
        Projection parameters as a CRS object or a dictionary or string of
        PROJ.4 parameters.

    Returns
    -------
    area_def : object
        AreaDefinition object
    """
    try:
        import rasterio
    except ImportError:
        rasterio = None
        try:
            from osgeo import gdal
        except ImportError:
            raise ImportError('Either rasterio or gdal must be available')

    cleanup_gdal = cleanup_rasterio = None
    if isinstance(source, str):
        if rasterio is not None:
            source = rasterio.open(source)
            cleanup_rasterio = True
        else:
            source = gdal.Open(source)
            cleanup_gdal = True

    try:
        if rasterio is not None and isinstance(source, (rasterio.io.DatasetReader, rasterio.io.DatasetWriter)):
            area_def = _get_area_def_from_rasterio(source, area_id, name, proj_id, projection)
        else:
            area_def = _get_area_def_from_gdal(source, area_id, name, proj_id, projection)
    finally:
        if cleanup_rasterio:
            source.close()
        elif cleanup_gdal:
            source = None

    return area_def if pyresample.config.get("features.future_geometries", False) else area_def.to_legacy()
