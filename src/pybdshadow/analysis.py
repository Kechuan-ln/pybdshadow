import pandas as pd
from suncalc import get_times
from shapely.geometry import MultiPolygon
import transbigdata as tbd
import geopandas as gpd
from .pybdshadow import (
    bdshadow_sunlight,
)
from .preprocess import bd_preprocess


def get_timetable(lon, lat, dates=['2022-01-01'], gap=3600, padding=1800):
    # generate timetable
    def get_timeSeries(day, lon, lat, gap=3600, padding=1800):
        date = pd.to_datetime(day+' 12:45:33.959797119')
        times = get_times(date, lon, lat)
        date_sunrise = times['sunrise']
        data_sunset = times['sunset']
        timestamp_sunrise = pd.Series(date_sunrise).astype('int')
        timestamp_sunset = pd.Series(data_sunset).astype('int')
        times = pd.to_datetime(pd.Series(range(
            timestamp_sunrise.iloc[0]+padding*1000000000,
            timestamp_sunset.iloc[0]-padding*1000000000,
            gap*1000000000)))
        return times
    dates = pd.DataFrame(pd.concat(
        [get_timeSeries(date, lon, lat, gap,padding) for date in dates]), columns=['datetime'])
    dates['date'] = dates['datetime'].apply(lambda r: str(r)[:19])
    return dates


def cal_sunshadows(buildings, cityname='somecity', dates=['2022-01-01'], gap=3600,
              roof=True, include_building=True,save_shadows=False,printlog=False):
    '''
    Calculate the sunlight shadow in different date with given time gap.

    **Parameters**

    buildings : GeoDataFrame
        Buildings. coordinate system should be WGS84
    cityname : string
        Cityname. If save_shadows, this function will create `result/cityname` folder to save the shadows
    dates : list
        list of dates
    gap : number
        time gap(s)
    roof : bool
        whether to calculate roof shadow.
    include_building : bool
        whether the shadow include building outline
    save_shadows : bool
        whether to save calculated shadows
    printlog : bool
        whether to print log

    **Return**

    allshadow : GeoDataFrame
        All building shadows calculated
    '''
    # 获取城市位置
    lon, lat = buildings['geometry'].iloc[0].bounds[:2]
    timetable = get_timetable(lon, lat, dates, gap)
    import os
    if save_shadows:
        if not os.path.exists('result'):
            os.mkdir('result')
        if not os.path.exists('result/'+cityname):
            os.mkdir('result/'+cityname)
    allshadow = []
    for i in range(len(timetable)):
        date = timetable['datetime'].iloc[i]
        name = timetable['date'].iloc[i]
        if not os.path.exists('result/'+cityname+'/roof_'+name+'.json'):
            if printlog:
                print('Calculating', cityname, ':', name)
            # Calculate shadows
            shadows = bdshadow_sunlight(
                buildings, date, roof=roof, include_building=include_building)
            shadows['date'] = date
            roof_shaodws = shadows[shadows['type'] == 'roof']
            ground_shaodws = shadows[shadows['type'] == 'ground']

            if save_shadows:
                if len(roof_shaodws)>0:
                    roof_shaodws.to_file(
                        'result/'+cityname+'/roof_'+name+'.json', driver='GeoJSON')
                if len(ground_shaodws)>0:
                    ground_shaodws.to_file(
                    'result/'+cityname+'/ground_'+name+'.json', driver='GeoJSON')
            allshadow.append(shadows)
    allshadow = pd.concat(allshadow)
    return allshadow


def cal_shadowcoverage(shadows_input,buildings,roof=True,gap = 3600,accuracy=1):
    '''
    Calculate the sunlight shadow coverage time for given area.

    **Parameters**

    shadows_input : GeoDataFrame
        All building shadows calculated
    buildings : GeoDataFrame
        Buildings. coordinate system should be WGS84
    roof : bool
        If true roof shadow, false then ground shadow
    gap : number
        time gap(s), which is for calculation of coverage time
    accuracy : number
        size of grids.

    **Return**
    
    bdgrids : GeoDataFrame
        grids generated by TransBigData in study area, each grids have a `time` column store the shadow coverage time

    '''
    shadows = bd_preprocess(shadows_input)
    if roof:
        ground_shadows = shadows[shadows['type']=='roof'].groupby(['date'])['geometry'].apply(
                    lambda df: MultiPolygon(list(df)).buffer(0)).reset_index()
        #研究区域
        bounds = buildings.unary_union.bounds
        
        bdgrids,params = tbd.area_to_grid(bounds,accuracy)
        buildings.crs = None
        bdgrids = gpd.sjoin(bdgrids,buildings)
    else:
        ground_shadows = shadows[shadows['type']=='ground'].groupby(['date'])['geometry'].apply(
                    lambda df: MultiPolygon(list(df)).buffer(0)).reset_index()

        #研究区域
        bounds = buildings.unary_union.bounds
        bdgrids,params = tbd.area_to_grid(bounds,accuracy)

        buildings.crs = None
        bdgrids = gpd.sjoin(bdgrids,buildings,how='left')
        bdgrids = bdgrids[bdgrids['index_right'].isnull()]

    gridcount = gpd.sjoin(bdgrids[['LONCOL','LATCOL','geometry']],ground_shadows[['geometry']]).\
        groupby(['LONCOL','LATCOL'])['geometry'].count().rename('count').reset_index()
    bdgrids = pd.merge(bdgrids,gridcount,how='left')
    bdgrids['time'] = bdgrids['count'].fillna(0)*gap

    return bdgrids
