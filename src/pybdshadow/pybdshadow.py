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
import pandas as pd
import geopandas as gpd
from suncalc import get_position
from shapely.geometry import Polygon
from shapely import geometry
import math
import numpy as np
import time
from .preprocess import merge_shadow


def calSunShadow_vector(shape, shapeHeight, sunPosition):
    # 多维数据类型：numpy
    # 输入的shape是一个矩阵（n*2*2) n个建筑物面，每个建筑有2个点，每个点有三个维度
    # shapeHeight(n) 每一栋建筑的高度都是一样的
    azimuth = sunPosition['azimuth']
    altitude = sunPosition['altitude']

    n = np.shape(shape)[0]
    distance = shapeHeight/math.tan(altitude)

    # 计算投影位置偏移

    lonDistance = distance*math.sin(azimuth)  # n个偏移量[n]
    lonDistance = lonDistance.reshape((n, 1))
    latDistance = distance*math.cos(azimuth)
    latDistance = latDistance.reshape((n, 1))

    shadowShape = np.zeros((n, 5, 2))  # n个建筑物面，每个面都有5个点，每个点都有个维数

    shadowShape[:, 0:2, :] += shape  # 前两个点不变
    shadowShape[:, 2:4, 0] = shape[:, :, 0] + lonDistance
    shadowShape[:, 2:4, 1] = shape[:, :, 1] + latDistance

    shadowShape[:, [2, 3], :] = shadowShape[:, [3, 2], :]
    shadowShape[:, 4, :] = shadowShape[:, 0, :]
    return shadowShape


def bdshadow_sunlight(buildings, date, merge=False, height='height', ground=0, epsg=3857):
    '''
    Calculate the sunlight shadow of the buildings.

    **Parameters**
    buildings : GeoDataFrame
        Buildings. coordinate system should be WGS84
    date : datetime
        Datetime
    merge : bool
        whether to merge the wall shadows into the building shadows
    height : string
        Column name of building height
    ground : number
        Height of the ground
    epsg : number
        epsg code of the projection coordinate system

    **Return**
    shadows : GeoDataFrame
        Building shadow
    '''
    start = time.time()
    building = buildings.copy()
    building[height] -= ground
    building = building[building[height] > 0]
    # calculate position
    lon1, lat1, lon2, lat2 = list(building.bounds.mean())
    lon = (lon1+lon2)/2
    lat = (lat1+lat2)/2
    # transform coordinate system
    building.crs = 'epsg:4326'
    building = building.to_crs(epsg=epsg)

    # obtain sun position
    sunPosition = get_position(date, lon, lat)
    buildingshadow = building.copy()
    # walls
    a = buildingshadow['geometry'].apply(lambda r: list(r.exterior.coords))
    buildingshadow['wall'] = a
    buildingshadow = buildingshadow.set_index(['building_id'])
    a = buildingshadow.apply(lambda x: pd.Series(x['wall']), axis=1).unstack()
    walls = a[- a.isnull()].reset_index().sort_values(by=['building_id', 'level_0'])
    walls = pd.merge(walls, buildingshadow['height'].reset_index())
    walls['x1'] = walls[0].apply(lambda r: r[0])
    walls['y1'] = walls[0].apply(lambda r: r[1])
    walls['x2'] = walls['x1'].shift(-1)
    walls['y2'] = walls['y1'].shift(-1)
    walls = walls[walls['building_id'] == walls['building_id'].shift(-1)]
    walls = walls[['x1', 'y1', 'x2', 'y2', 'building_id', 'height']]
    walls['wall'] = walls.apply(lambda r: [[r['x1'], r['y1']],
                                           [r['x2'], r['y2']]], axis=1)
    walls_shape = np.array(list(walls['wall']))
    end = time.time()
    print('Running time: %s Seconds' % (end - start))
    # calculate shadow for walls
    
    shadowShape = calSunShadow_vector(
        walls_shape, walls['height'].values, sunPosition)
    end = time.time()
    print('Running time: %s Seconds' % (end - start))
    walls['geometry'] = list(shadowShape)
    walls['geometry'] = walls['geometry'].apply(lambda r: Polygon(r))
    walls = gpd.GeoDataFrame(walls)

    walls.crs = 'epsg:'+str(epsg)
    shadows = walls[['building_id', 'geometry']].to_crs(epsg=4326)
    if merge:
        shadows = merge_shadow(shadows)
    end = time.time()
    print('Running time: %s Seconds' % (end - start))
    return shadows



def lonlat_mercator(lonlat):
    mercator = [0,0]
    earthRad = 6378137.0
    mercator[0] = lonlat[0] * math.pi/ 180 * earthRad #角度转弧度
    a = lonlat[1] * math.pi / 180; #弧度制纬度
    mercator[1]= earthRad / 2 * math.log((1.0 + math.sin(a)) / (1.0 - math.sin(a)))
    return mercator

#[:,2]
def lonlat_mercator_vector(lonlat):
    mercator = np.zeros_like(lonlat)
    earthRad = 6378137.0
    mercator[:,:,0] = lonlat[:,:,0] * math.pi/ 180 * earthRad #角度转弧度
    a = lonlat[:,:,1] * math.pi / 180; #弧度制纬度
    mercator[:,:,1]= earthRad / 2 * np.log((1.0 + np.sin(a)) / (1.0 - np.sin(a)))
    return mercator

def mercator_lonlat(mercator):
    lonlat = [0,0]
    lonlat[0] = mercator[0]/20037508.34*180
    lonlat[1] = mercator[1]/20037508.34*180
    lonlat[1]= 180/math.pi*(2*math.atan(math.exp(lonlat[1]*math.pi/180))-math.pi/2)
     
    return lonlat

def mercator_lonlat_vector(mercator):
    lonlat = np.zeros_like(mercator)
    lonlat[:,:,0] = mercator[:,:,0]/20037508.34*180
    lonlat[:,:,1] = mercator[:,:,1]/20037508.34*180
    lonlat[:,:,1] = 180/math.pi*(2*np.arctan(np.exp(lonlat[:,:,1]*math.pi/180))-math.pi/2)
     
    return lonlat


def calSunShadow_vector1(shape, shapeHeight, sunPosition):
    # 多维数据类型：numpy
    # 输入的shape是一个矩阵（n*2*2) n个建筑物面，每个建筑有2个点，每个点有三个维度
    # shapeHeight(n) 每一栋建筑的高度都是一样的
    
    # 坐标系转换transform coordinate system
    shape = lonlat_mercator_vector(shape)
    #print(shape,np.shape(shape))
    
    azimuth = sunPosition['azimuth']
    altitude = sunPosition['altitude']

    n = np.shape(shape)[0]
    distance = shapeHeight/math.tan(altitude)

    # 计算投影位置偏移
    lonDistance = distance*math.sin(azimuth)  # n个偏移量[n]
    lonDistance = lonDistance.reshape((n, 1))
    latDistance = distance*math.cos(azimuth)
    latDistance = latDistance.reshape((n, 1))

    shadowShape = np.zeros((n, 5, 2))  # n个建筑物面，每个面都有5个点，每个点都有个维数

    shadowShape[:, 0:2, :] += shape  # 前两个点不变
    shadowShape[:, 2:4, 0] = shape[:, :, 0] + lonDistance
    shadowShape[:, 2:4, 1] = shape[:, :, 1] + latDistance

    shadowShape[:, [2, 3], :] = shadowShape[:, [3, 2], :]
    shadowShape[:, 4, :] = shadowShape[:, 0, :]
    
    shadowShape = mercator_lonlat_vector(shadowShape)
    #print(shadowShape,np.shape(shadowShape))
    return shadowShape

#def mLonlat():
    

def bdshadow_sunlight1(buildings, date, merge=False, height='height', ground=0, epsg=3857):
    '''
    Calculate the sunlight shadow of the buildings.

    **Parameters**
    buildings : GeoDataFrame
        Buildings. coordinate system should be WGS84
    date : datetime
        Datetime
    merge : bool
        whether to merge the wall shadows into the building shadows
    height : string
        Column name of building height
    ground : number
        Height of the ground
    epsg : number
        epsg code of the projection coordinate system

    **Return**
    shadows : GeoDataFrame
        Building shadow
    '''
    start = time.time()
    
    building = buildings.copy()
     
    building[height] -= ground
    building = building[building[height] > 0]
    
    # calculate position
    lon1, lat1, lon2, lat2 = list(building.bounds.mean())
    lon = (lon1+lon2)/2
    lat = (lat1+lat2)/2
    
    #测试坐标转换函数是否可行
    #points = gpd.GeoSeries([geometry.Point(lon,lat)],crs='EPSG:4326') # 指定坐标系为WGS 1984                                     
    #points2 = points.to_crs(epsg=epsg) #用自带的函数计算
    #points1 = lonlat_mercator([lon,lat])#用自定义的函数计算
    #print("zidong",points2,points1)
            
    # obtain sun position
    sunPosition = get_position(date, lon, lat)
    buildingshadow = building.copy()
    
    a = buildingshadow['geometry'].apply(lambda r: list(r.exterior.coords))
    buildingshadow['wall'] = a
    buildingshadow = buildingshadow.set_index(['building_id'])
    a = buildingshadow.apply(lambda x: pd.Series(x['wall']), axis=1).unstack()
    walls = a[- a.isnull()].reset_index().sort_values(by=['building_id', 'level_0'])
    walls = pd.merge(walls, buildingshadow['height'].reset_index())
    walls['x1'] = walls[0].apply(lambda r: r[0])
    walls['y1'] = walls[0].apply(lambda r: r[1])
    walls['x2'] = walls['x1'].shift(-1)
    walls['y2'] = walls['y1'].shift(-1)
    walls = walls[walls['building_id'] == walls['building_id'].shift(-1)]
    walls = walls[['x1', 'y1', 'x2', 'y2', 'building_id', 'height']]
    walls['wall'] = walls.apply(lambda r: [[r['x1'], r['y1']],
                                           [r['x2'], r['y2']]], axis=1)
    walls_shape = np.array(list(walls['wall']))
    
    end = time.time()
    print('Running time: %s Seconds' % (end - start))
    
    # calculate shadow for walls
    shadowShape = calSunShadow_vector1(
        walls_shape, walls['height'].values, sunPosition)
    end = time.time()
    print('Running time: %s Seconds' % (end - start))
    
    walls['geometry'] = list(shadowShape)
    walls['geometry'] = walls['geometry'].apply(lambda r: Polygon(r))
    walls = gpd.GeoDataFrame(walls)
    
    if merge:
        walls = merge_shadow(walls)
        
    end = time.time()
    print('Running time: %s Seconds' % (end - start))
    return walls


'''
待开发功能:
1. 广告阴影计算
'''
