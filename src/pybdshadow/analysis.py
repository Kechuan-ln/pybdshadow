import pandas as pd
from suncalc import get_times
from shapely.geometry import MultiPolygon
import transbigdata as tbd
import geopandas as gpd
from .pybdshadow import (
    bdshadow_sunlight,
)
from .preprocess import bd_preprocess


def get_timetable(lon, lat, dates=['2022-01-01'], precision=3600, padding=1800):
    # generate timetable with given interval
    def get_timeSeries(day, lon, lat, precision=3600, padding=1800):
        date = pd.to_datetime(day+' 12:45:33.959797119')
        times = get_times(date, lon, lat)
        date_sunrise = times['sunrise']
        data_sunset = times['sunset']
        timestamp_sunrise = pd.Series(date_sunrise).astype('int')
        timestamp_sunset = pd.Series(data_sunset).astype('int')
        times = pd.to_datetime(pd.Series(range(
            timestamp_sunrise.iloc[0]+padding*1000000000,
            timestamp_sunset.iloc[0]-padding*1000000000,
            precision*1000000000)))
        return times
    dates = pd.DataFrame(pd.concat(
        [get_timeSeries(date, lon, lat, precision, padding) for date in dates]), columns=['datetime'])
    dates['date'] = dates['datetime'].apply(lambda r: str(r)[:19])
    return dates


def cal_sunshine(buildings, day='2022-01-01', roof=False, grids=gpd.GeoDataFrame(), accuracy=1, precision=3600, padding=1800):
    '''
    Calculate the sunshine time in given date.

    Parameters
    --------------------
    buildings : GeoDataFrame
        Buildings. coordinate system should be WGS84
    day : str
        the day to calculate the sunshine
    roof : bool
        whether to calculate roof shadow.
    grids : GeoDataFrame
        grids generated by TransBigData in study area
    precision : number
        time precision(s)
    padding : number
        padding time before and after sunrise and sunset
    accuracy : number
        size of grids. Produce vector polygons if set as `vector` 

    Return
    ----------
    grids : GeoDataFrame
        grids generated by TransBigData in study area, each grids have a `time` column store the sunshine time

    '''
    # calculate day time duration
    lon, lat = buildings['geometry'].iloc[0].bounds[:2]
    date = pd.to_datetime(day+' 12:45:33.959797119')
    times = get_times(date, lon, lat)
    date_sunrise = times['sunrise']
    data_sunset = times['sunset']
    timestamp_sunrise = pd.Series(date_sunrise).astype('int')
    timestamp_sunset = pd.Series(data_sunset).astype('int')
    sunlighthour = (
        timestamp_sunset.iloc[0]-timestamp_sunrise.iloc[0])/(1000000000*3600)

    # Generate shadow every time interval
    shadows = cal_sunshadows(
        buildings, dates=[day], precision=precision, padding=padding)
    if accuracy == 'vector':
        if roof:
            shadows = shadows[shadows['type'] == 'roof']
            shadows = bd_preprocess(shadows)
            shadows = shadows.groupby(['date', 'type'])['geometry'].apply(
                lambda df: MultiPolygon(list(df)).buffer(0)).reset_index()
            shadows = bd_preprocess(shadows)
            shadows = count_overlapping_features(shadows)
        else:
            shadows = shadows[shadows['type'] == 'ground']
            shadows = bd_preprocess(shadows)
            shadows = shadows.groupby(['date', 'type'])['geometry'].apply(
                lambda df: MultiPolygon(list(df)).buffer(0)).reset_index()
            shadows = bd_preprocess(shadows)
            shadows = count_overlapping_features(shadows)

        shadows['time'] = shadows['count']*precision
        shadows['Hour'] = sunlighthour-shadows['time']/3600
        shadows.loc[shadows['Hour'] <= 0, 'Hour'] = 0
        return shadows
    else:
        # Grid analysis of shadow cover duration(ground).
        grids = cal_shadowcoverage(
            shadows, buildings, grids=grids, roof=roof, precision=precision, accuracy=accuracy)

        grids['Hour'] = sunlighthour-grids['time']/3600
        return grids


def cal_sunshadows(buildings, cityname='somecity', dates=['2022-01-01'], precision=3600, padding=1800,
                   roof=True, include_building=True, save_shadows=False, printlog=False):
    '''
    Calculate the sunlight shadow in different date with given time precision.

    Parameters
    --------------------
    buildings : GeoDataFrame
        Buildings. coordinate system should be WGS84
    cityname : string
        Cityname. If save_shadows, this function will create `result/cityname` folder to save the shadows
    dates : list
        List of dates
    precision : number
        Time precision(s)
    padding : number
        Padding time (second) before and after sunrise and sunset. Should be over 1800s to avoid sun altitude under 0
    roof : bool
        whether to calculate roof shadow.
    include_building : bool
        whether the shadow include building outline
    save_shadows : bool
        whether to save calculated shadows
    printlog : bool
        whether to print log

    Return
    ----------
    allshadow : GeoDataFrame
        All building shadows calculated
    '''
    if (padding < 1800):
        raise ValueError(
            'Padding time should be over 1800s to avoid sun altitude under 0')  # pragma: no cover
    # obtain city location
    lon, lat = buildings['geometry'].iloc[0].bounds[:2]
    timetable = get_timetable(lon, lat, dates, precision, padding)
    import os
    if save_shadows:
        if not os.path.exists('result'):             # pragma: no cover
            os.mkdir('result')                       # pragma: no cover
        if not os.path.exists('result/'+cityname):   # pragma: no cover
            os.mkdir('result/'+cityname)             # pragma: no cover
    allshadow = []
    for i in range(len(timetable)):
        date = timetable['datetime'].iloc[i]
        name = timetable['date'].iloc[i]
        if not os.path.exists('result/'+cityname+'/roof_'+name+'.json'):
            if printlog:
                print('Calculating', cityname, ':', name)    # pragma: no cover
            # Calculate shadows
            shadows = bdshadow_sunlight(
                buildings, date, roof=roof, include_building=include_building)
            shadows['date'] = date
            roof_shaodws = shadows[shadows['type'] == 'roof']
            ground_shaodws = shadows[shadows['type'] == 'ground']

            if save_shadows:
                if len(roof_shaodws) > 0:    # pragma: no cover
                    roof_shaodws.to_file(    # pragma: no cover
                        'result/'+cityname+'/roof_'+name+'.json', driver='GeoJSON')  # pragma: no cover
                if len(ground_shaodws) > 0:  # pragma: no cover
                    ground_shaodws.to_file(  # pragma: no cover
                        'result/'+cityname+'/ground_'+name+'.json', driver='GeoJSON')  # pragma: no cover
            allshadow.append(shadows)
    allshadow = pd.concat(allshadow)
    return allshadow


def cal_shadowcoverage(shadows_input, buildings, grids=gpd.GeoDataFrame(), roof=True, precision=3600, accuracy=1):
    '''
    Calculate the sunlight shadow coverage time for given area.

    Parameters
    --------------------
    shadows_input : GeoDataFrame
        All building shadows calculated
    buildings : GeoDataFrame
        Buildings. coordinate system should be WGS84
    grids : GeoDataFrame
        grids generated by TransBigData in study area
    roof : bool
        If true roof shadow, false then ground shadow
    precision : number
        time precision(s), which is for calculation of coverage time
    accuracy : number
        size of grids.

    Return
    --------------------
    grids : GeoDataFrame
        grids generated by TransBigData in study area, each grids have a `time` column store the shadow coverage time

    '''
    shadows = bd_preprocess(shadows_input)

    # study area
    bounds = buildings.unary_union.bounds
    if len(grids) == 0:
        grids, params = tbd.area_to_grid(bounds, accuracy)

    if roof:
        ground_shadows = shadows[shadows['type'] == 'roof'].groupby(['date'])['geometry'].apply(
            lambda df: MultiPolygon(list(df)).buffer(0)).reset_index()

        buildings.crs = None
        grids = gpd.sjoin(grids, buildings)
    else:
        ground_shadows = shadows[shadows['type'] == 'ground'].groupby(['date'])['geometry'].apply(
            lambda df: MultiPolygon(list(df)).buffer(0)).reset_index()

        buildings.crs = None
        grids = gpd.sjoin(grids, buildings, how='left')
        grids = grids[grids['index_right'].isnull()]

    gridcount = gpd.sjoin(grids[['LONCOL', 'LATCOL', 'geometry']], ground_shadows[['geometry', 'date']]).\
        drop_duplicates(subset=['LONCOL', 'LATCOL', 'date']).groupby(['LONCOL', 'LATCOL'])['geometry'].\
        count().rename('count').reset_index()
    grids = pd.merge(grids, gridcount, how='left')
    grids['time'] = grids['count'].fillna(0)*precision

    return grids


def count_overlapping_features(gdf):
    import shapely
    bounds = gdf.geometry.exterior.unary_union
    new_polys = list(shapely.ops.polygonize(bounds))
    new_gdf = gpd.GeoDataFrame(geometry=new_polys)
    new_gdf['id'] = range(len(new_gdf))
    new_gdf_centroid = new_gdf.copy()
    new_gdf_centroid['geometry'] = new_gdf.centroid
    overlapcount = gpd.sjoin(new_gdf_centroid, gdf)
    overlapcount = overlapcount.groupby(
        ['id'])['index_right'].count().rename('count').reset_index()
    out_gdf = pd.merge(new_gdf, overlapcount)
    return out_gdf
