"""
BSD 3-Clause License

Copyright (c) 2022, Qing Yu
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon
import pandas as pd

def ad_to_gdf(ad_params,billboard_height = 10):
    '''
    Generate a GeoDataFrame from ad_params for visualization.

    **Parameters**
    ad_params : dict
        Parameters of advertisement.
    billboard_height : number
        The height of the billboard
    
        
    **Return**
    ad_gdf : GeoDataFrame
        advertisment GeoDataFrame
    '''
    ad_gdf = []   
    width = 0.02     
    gap = 0.000001
    if ('point1' in ad_params)&('point2' in ad_params):
        adp1 = ad_params['point1']
        adp2 = ad_params['point2']

        billboard_gdf = gpd.GeoDataFrame({'geometry': [
                Polygon([[adp1[0],adp1[1],ad_params['height']],
                [adp1[0]+gap,adp1[1]+gap,ad_params['height']+billboard_height],
                [adp2[0]+gap,adp2[1]+gap,ad_params['height']+billboard_height],
                [adp2[0],adp2[1],ad_params['height']]]),
                Polygon([
                [(adp1[0]+ adp2[0]) / 2 - width * (adp2[0]- adp1[0]) - gap, (adp1[1] + adp2[1]) / 2 - width * (adp2[1] - adp1[1]) - gap, ad_params['height']],
                [width * (adp2[0]- adp1[0]) + (adp1[0]+ adp2[0]) / 2 - gap, width * (adp2[1] - adp1[1]) + (adp1[1] + adp2[1]) / 2 - gap, ad_params['height']],
                [width * (adp2[0]- adp1[0]) + (adp1[0]+ adp2[0]) / 2, width * (adp2[1] - adp1[1]) + (adp1[1] + adp2[1]) / 2, 0],
                [(adp1[0]+ adp2[0]) / 2 - width * (adp2[0]- adp1[0]), (adp1[1] + adp2[1]) / 2 - width * (adp2[1] - adp1[1]), 0],
                ]
            ),]})
        ad_gdf.append(billboard_gdf)

    if 'brandCenter' in ad_params:
        brandCenter = ad_params['brandCenter'][:2]
        adcenter_gdf = gpd.GeoDataFrame({'geometry': [
                Polygon([
                [brandCenter[0]-width/2000,brandCenter[1]-width/2000, 0],
                [brandCenter[0]-width/2000-gap,brandCenter[1]-width/2000-gap, ad_params['height']],
                [brandCenter[0]+width/2000-gap,brandCenter[1]+width/2000-gap, ad_params['height']],
                [brandCenter[0]+width/2000,brandCenter[1]+width/2000, 0]
                ]
            ),]})
        ad_gdf.append(adcenter_gdf)

    ad_gdf = gpd.GeoDataFrame(pd.concat(ad_gdf))
    return ad_gdf


def show_bdshadow(buildings=gpd.GeoDataFrame(),
                  shadows=gpd.GeoDataFrame(),
                  ad=gpd.GeoDataFrame(),
                  ad_visualArea=gpd.GeoDataFrame(),
                  height='height',
                  zoom='auto'):
    '''
    Visualize the building and shadow with keplergl.

    **Parameters**
    buildings : GeoDataFrame
        Buildings. coordinate system should be WGS84
    shadows : GeoDataFrame
        Building shadows. coordinate system should be WGS84
    ad : GeoDataFrame
        Advertisment. coordinate system should be WGS84
    ad_visualArea : GeoDataFrame
        Visualarea of Advertisment. coordinate system should be WGS84
    height : string
        Column name of building height
    zoom : number
        Zoom level of the map

    **Return**
    vmap : keplergl.keplergl.KeplerGl
        Visualizations provided by keplergl
    '''
    displaybuilding = buildings.copy()
    displaybuildingshadow = shadows.copy()
    displayad = ad.copy()
    displayad_visualArea = ad_visualArea.copy()
    vmapdata = {}
    layers = []
    if len(displayad_visualArea) == 0:
        displayad_visualArea['geometry'] = []
        displayad_visualArea[height] = []
    else:

        bdcentroid = displayad_visualArea['geometry'].bounds[[
            'minx', 'miny', 'maxx', 'maxy']]
        lon_center, lat_center = bdcentroid['minx'].mean(
        ), bdcentroid['miny'].mean()
        lon_min, lon_max = bdcentroid['minx'].min(), bdcentroid['maxx'].max()
        vmapdata['ad_visualArea'] = displayad_visualArea
        layers.append(
            {'id': 'lz48o1',
             'type': 'geojson',
                     'config': {
                         'dataId': 'ad_visualArea',
                         'label': 'ad_visualArea',
                         'color': [255, 255, 0],
                         'highlightColor': [252, 242, 26, 255],
                         'columns': {'geojson': 'geometry'},
                         'isVisible': True,
                         'visConfig': {
                             'opacity': 0.32,
                             'strokeOpacity': 0.8,
                             'thickness': 0.5,
                             'strokeColor': [255, 153, 31],
                             'colorRange': {'name': 'Global Warming',
                                            'type': 'sequential',
                                            'category': 'Uber',
                                            'colors': ['#5A1846',
                                                       '#900C3F',
                                                       '#C70039',
                                                       '#E3611C',
                                                       '#F1920E',
                                                       '#FFC300']},
                             'strokeColorRange': {'name': 'Global Warming',
                                                  'type': 'sequential',
                                                  'category': 'Uber',
                                                  'colors': ['#5A1846',
                                                             '#900C3F',
                                                             '#C70039',
                                                             '#E3611C',
                                                             '#F1920E',
                                                             '#FFC300']},
                             'radius': 10,
                             'sizeRange': [0, 10],
                             'radiusRange': [0, 50],
                             'heightRange': [0, 500],
                             'elevationScale': 5,
                             'enableElevationZoomFactor': True,
                             'stroked': False,
                             'filled': True,
                             'enable3d': False,
                             'wireframe': False},
                         'hidden': False,
                         'textLabel': [{
                             'field': None,
                                       'color': [255, 255, 255],
                                       'size': 18,
                                       'offset': [0, 0],
                                       'anchor': 'start',
                                       'alignment': 'center'}]},
                     'visualChannels': {
                         'colorField': None,
                         'colorScale': 'quantile',
                         'strokeColorField': None,
                         'strokeColorScale': 'quantile',
                         'sizeField': None,
                         'sizeScale': 'linear',
                         'heightField': None,
                         'heightScale': 'linear',
                                        'radiusField': None,
                                        'radiusScale': 'linear'}})
    if len(displayad) == 0:
        displayad['geometry'] = []
        displayad[height] = []
    else:
        vmapdata['advertisment'] = displayad
        layers.append(
            {'id': 'lz48o2',
             'type': 'geojson',
                     'config': {
                         'dataId': 'advertisment',
                         'label': 'advertisment',
                         'color': [255, 0, 0],
                         'highlightColor': [252, 242, 26, 255],
                         'columns': {'geojson': 'geometry'},
                         'isVisible': True,
                         'visConfig': {
                             'opacity': 0.32,
                             'strokeOpacity': 0.8,
                             'thickness': 0.5,
                             'strokeColor': [255, 153, 31],
                             'colorRange': {'name': 'Global Warming',
                                            'type': 'sequential',
                                            'category': 'Uber',
                                            'colors': ['#5A1846',
                                                       '#900C3F',
                                                       '#C70039',
                                                       '#E3611C',
                                                       '#F1920E',
                                                       '#FFC300']},
                             'strokeColorRange': {'name': 'Global Warming',
                                                  'type': 'sequential',
                                                  'category': 'Uber',
                                                  'colors': ['#5A1846',
                                                             '#900C3F',
                                                             '#C70039',
                                                             '#E3611C',
                                                             '#F1920E',
                                                             '#FFC300']},
                             'radius': 10,
                             'sizeRange': [0, 10],
                             'radiusRange': [0, 50],
                             'heightRange': [0, 500],
                             'elevationScale': 5,
                             'enableElevationZoomFactor': True,
                             'stroked': False,
                             'filled': True,
                             'enable3d': False,
                             'wireframe': False},
                         'hidden': False,
                         'textLabel': [{
                             'field': None,
                                       'color': [255, 255, 255],
                                       'size': 18,
                                       'offset': [0, 0],
                                       'anchor': 'start',
                                       'alignment': 'center'}]},
                     'visualChannels': {
                         'colorField': None,
                         'colorScale': 'quantile',
                         'strokeColorField': None,
                         'strokeColorScale': 'quantile',
                         'sizeField': None,
                         'sizeScale': 'linear',
                         'heightField': None,
                         'heightScale': 'linear',
                                        'radiusField': None,
                                        'radiusScale': 'linear'}})
        bdcentroid = displayad['geometry'].bounds[[
            'minx', 'miny', 'maxx', 'maxy']]
        lon_center, lat_center = bdcentroid['minx'].mean(
        ), bdcentroid['miny'].mean()
        lon_min, lon_max = bdcentroid['minx'].min(), bdcentroid['maxx'].max()

    if len(displaybuilding) == 0:
        displaybuilding['geometry'] = []
        displaybuilding[height] = []
    else:
        vmapdata['building'] = displaybuilding
        layers.append({
            'id': 'lz48o3',
            'type': 'geojson',
            'config': {
                'dataId': 'building',
                'label': 'building',
                'color': [169, 203, 237],
                'highlightColor': [252, 242, 26, 255],
                'columns': {'geojson': 'geometry'},
                'isVisible': True,
                'visConfig': {
                    'opacity': 0.8,
                    'strokeOpacity': 0.8,
                    'thickness': 0.5,
                    'strokeColor': [221, 178, 124],
                    'colorRange': {
                        'name': 'Global Warming',
                        'type': 'sequential',
                        'category': 'Uber',
                                    'colors': ['#5A1846',
                                               '#900C3F',
                                               '#C70039',
                                               '#E3611C',
                                               '#F1920E',
                                               '#FFC300']},
                    'strokeColorRange': {'name': 'Global Warming',
                                         'type': 'sequential',
                                         'category': 'Uber',
                                                     'colors': ['#5A1846',
                                                                '#900C3F',
                                                                '#C70039',
                                                                '#E3611C',
                                                                '#F1920E',
                                                                '#FFC300']},
                                'radius': 10,
                                'sizeRange': [0, 10],
                                'radiusRange': [0, 50],
                                'heightRange': [0, 500],
                                'elevationScale': 0.5,
                                'enableElevationZoomFactor': True,
                                'stroked': False,
                                'filled': True,
                                'enable3d': True,
                                'wireframe': False},
                'hidden': False,
                'textLabel': [{'field': None,
                               'color': [255, 255, 255],
                               'size': 18,
                               'offset': [0, 0],
                               'anchor': 'start',
                               'alignment': 'center'}]},
            'visualChannels': {'colorField': None,
                               'colorScale': 'quantile',
                               'strokeColorField': None,
                               'strokeColorScale': 'quantile',
                               'sizeField': None,
                               'sizeScale': 'linear',
                               'heightField': {
                                   'name': 'height',
                                   'type': 'integer'},
                               'heightScale': 'linear',
                               'radiusField': None,
                               'radiusScale': 'linear'}})
        bdcentroid = displaybuilding['geometry'].bounds[[
            'minx', 'miny', 'maxx', 'maxy']]
        lon_center, lat_center = bdcentroid['minx'].mean(
        ), bdcentroid['miny'].mean()
        lon_min, lon_max = bdcentroid['minx'].min(), bdcentroid['maxx'].max()
    if len(displaybuildingshadow) == 0:
        displaybuildingshadow['geometry'] = []
    else:
        bdcentroid = displaybuildingshadow['geometry'].bounds[[
            'minx', 'miny', 'maxx', 'maxy']]
        lon_center, lat_center = bdcentroid['minx'].mean(
        ), bdcentroid['miny'].mean()
        lon_min, lon_max = bdcentroid['minx'].min(), bdcentroid['maxx'].max()
        vmapdata['shadow'] = displaybuildingshadow
        layers.append(
            {'id': 'lz48o4',
             'type': 'geojson',
                     'config': {
                         'dataId': 'shadow',
                         'label': 'shadow',
                         'color': [73, 73, 73],
                         'highlightColor': [252, 242, 26, 255],
                         'columns': {'geojson': 'geometry'},
                         'isVisible': True,
                         'visConfig': {
                             'opacity': 0.32,
                             'strokeOpacity': 0.8,
                             'thickness': 0.5,
                             'strokeColor': [255, 153, 31],
                             'colorRange': {'name': 'Global Warming',
                                            'type': 'sequential',
                                            'category': 'Uber',
                                            'colors': ['#5A1846',
                                                       '#900C3F',
                                                       '#C70039',
                                                       '#E3611C',
                                                       '#F1920E',
                                                       '#FFC300']},
                             'strokeColorRange': {'name': 'Global Warming',
                                                  'type': 'sequential',
                                                  'category': 'Uber',
                                                  'colors': ['#5A1846',
                                                             '#900C3F',
                                                             '#C70039',
                                                             '#E3611C',
                                                             '#F1920E',
                                                             '#FFC300']},
                             'radius': 10,
                             'sizeRange': [0, 10],
                             'radiusRange': [0, 50],
                             'heightRange': [0, 500],
                             'elevationScale': 5,
                             'enableElevationZoomFactor': True,
                             'stroked': False,
                             'filled': True,
                             'enable3d': False,
                             'wireframe': False},
                         'hidden': False,
                         'textLabel': [{
                             'field': None,
                                       'color': [255, 255, 255],
                                       'size': 18,
                                       'offset': [0, 0],
                                       'anchor': 'start',
                                       'alignment': 'center'}]},
                     'visualChannels': {
                         'colorField': None,
                         'colorScale': 'quantile',
                         'strokeColorField': None,
                         'strokeColorScale': 'quantile',
                         'sizeField': None,
                         'sizeScale': 'linear',
                         'heightField': None,
                         'heightScale': 'linear',
                                        'radiusField': None,
                                        'radiusScale': 'linear'}})
    try:
        from keplergl import KeplerGl
    except ImportError:
        raise ImportError(
            "Please install keplergl, run "
            "the following code in cmd: pip install keplergl")

    if zoom == 'auto':
        zoom = 8.5-np.log(lon_max-lon_min)/np.log(2)
    vmap = KeplerGl(config={
        'version': 'v1',
        'config': {
            'visState': {
                'filters': [],
                'layers': layers,
                'layerBlending': 'normal',
                'animationConfig': {'currentTime': None, 'speed': 1}},
            'mapState': {'bearing': -3,
                         'dragRotate': True,
                         'latitude': lat_center,
                         'longitude': lon_center,
                         'pitch': 50,
                         'zoom': zoom,
                         'isSplit': False},
            'mapStyle': {'styleType': 'light',
                         'topLayerGroups': {},
                         'visibleLayerGroups': {'label': True,
                                                'road': True,
                                                'border': False,
                                                'building': True,
                                                'water': True,
                                                'land': True},
                         'mapStyles': {}}}}, data=vmapdata, height=500)
    return vmap
