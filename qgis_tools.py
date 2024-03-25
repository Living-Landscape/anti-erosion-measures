from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsApplication  # Add this line if QgsApplication is needed in your function
from qgis.core import QgsRasterLayer
from qgis.analysis import QgsNativeAlgorithms  # Add this line if needed
from datetime import datetime

import os 
import processing
import string
import random 
import time

def createoutputpathdir(pre_path,folder_name):  # Create a folder name based on the timestamp and defined name
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") #create timeprint

    folder_time = f"{timestamp}" #create a folder time name
    folder_name = ''.join([folder_name,folder_time]) #join folder name parts

    output_path_dir = os.path.join(pre_path, folder_name)
    print(output_path_dir)
    os.makedirs(output_path_dir, exist_ok=True) #creates a folder in directory

    return output_path_dir

def createoutputpathascii(pre_path,folder_name):  # Create a unique folder name based on the timestamp and additional 10 ascci letters
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") #create timeprint

    folder_time = f"{timestamp}" #create a folder name
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=10)) # 10char ascii random string
    folder_name = ''.join([folder_time,folder_name,random_string])

    output_pathascii = os.path.join(pre_path, folder_name)
    print(output_pathascii)
    os.makedirs(output_pathascii, exist_ok=True) #creates a folder in directory

    return output_pathascii

def simplifycontour(contour,path_dict): #simplify contour

    output_path = createoutputpathascii(path_dict,'simplified_geometry')

    simplifyed_contour = processing.run("native:simplifygeometries",\
     {'INPUT':contour,\
      'METHOD':2,\
      'TOLERANCE':4,\
      'OUTPUT':os.path.join(output_path, 'output.shp')})
    simplifyed_contour_layer = simplifyed_contour['OUTPUT']

    return simplifyed_contour_layer

def contourelevation(raster,path_dict,elevation): #calculate a single countour in a defined elevation
    output_path = createoutputpathascii(path_dict,'countour')
    contour = processing.run("gdal:contour",\
                    {'INPUT':raster,\
                    'BAND':1,\
                    'INTERVAL':10,\
                    'FIELD_NAME':'ELEV',\
                    'CREATE_3D':False,\
                    'IGNORE_NODATA':False,\
                    'NODATA':None,\
                    'OFFSET':0,\
                    'EXTRA':elevation,\
                    'OUTPUT':os.path.join(output_path, 'output.shp')})
    contour_layer = contour['OUTPUT'] 
    return contour_layer

def pointsalongline(vector,path_dict): #sample point along vector line 
    output_path = createoutputpathascii(path_dict, 'points_along_line')
    points = processing.run("native:pointsalonglines",\
                   {'INPUT':vector,\
                    'DISTANCE':10,\
                    'START_OFFSET':0,\
                    'END_OFFSET':0,\
                    'OUTPUT':os.path.join(output_path, 'output.shp')})
    points_layer = points['OUTPUT']
    return points_layer

def deletecolumns(points,path_dict): #delete column in atribute table 
    output_path = createoutputpathascii(path_dict, 'deleted_column')
    deletedcolumns = processing.run("qgis:deletecolumn",
                    {'INPUT':points,
                    'COLUMN': ['fid', 'ID', 'distance','angle'],  # Replace with the actual field names to be deleted
                    'OUTPUT': os.path.join(output_path, 'output.shp')})
    deletedcolumns_table = deletedcolumns['OUTPUT']
    return deletedcolumns_table

def calculateshortestlines(points1,points2,path_dict): #calculate shortes lines
    output_path = createoutputpathascii(path_dict,'calculated_shortest_lines')
    shortestlines = processing.run("native:shortestline",\
                    {'SOURCE':points1,\
                    'DESTINATION':points2,\
                    'METHOD':0,'NEIGHBORS':1,'DISTANCE':None,\
                    'OUTPUT':os.path.join(output_path, 'output.shp')})
    shortestlines_layer = shortestlines['OUTPUT']
    return shortestlines_layer, output_path

def buffering(vector, distance, path_dict): #perform a buffer zone around vector line 
    output_path = createoutputpathascii(path_dict,'buffer_zones')
    buffer = processing.run("native:buffer",\
                    {'INPUT':vector,\
                    'DISTANCE':distance,\
                    'SEGMENTS':5,\
                    'END_CAP_STYLE':0,\
                    'JOIN_STYLE':2,\
                    'MITER_LIMIT':2,\
                    'DISSOLVE':False,\
                    'OUTPUT':os.path.join(output_path, 'output.shp')})
    buffer_output = buffer['OUTPUT'] 
    return buffer, buffer_output

def filterDEM(raster, path_dict): #filter DEM from problem areas
    output_path = createoutputpathascii(path_dict,'filtered_DEM')


    depresionlessDEM = processing.run("grass7:r.fill.dir",\
                    {'input':raster,\
                    'format':0,\
                    '-f':False,\
                    'output':os.path.join(output_path, 'output.tif'),\
                    'direction':'TEMPORARY_OUTPUT',\
                    'areas':'TEMPORARY_OUTPUT',\
                    'GRASS_REGION_PARAMETER':None,\
                    'GRASS_REGION_CELLSIZE_PARAMETER':0,\
                    'GRASS_RASTER_FORMAT_OPT':'',\
                    'GRASS_RASTER_FORMAT_META':''})
    
    depresionlessDEM_output = depresionlessDEM['output']
    return depresionlessDEM_output

def watershed(raster, path_dict, threshold1): #calculate watershed
    output_path = createoutputpathascii(path_dict,'watershed')
    watershed_raster = processing.run("grass7:r.watershed",\
                    {'elevation':raster,\
                    'depression':None,\
                    'flow':None,\
                    'disturbed_land':None,\
                    'blocking':None,\
                    'threshold':threshold1,\
                    'max_slope_length':None,\
                    'convergence':5,\
                    'memory':300,\
                    '-s':False,\
                    '-m':True,\
                    '-4':False,\
                    '-a':False,\
                    '-b':False,\
                    'accumulation':'TEMPORARY_OUTPUT',\
                    'drainage':'TEMPORARY_OUTPUT',\
                    'basin':'TEMPORARY_OUTPUT',\
                    'stream':os.path.join(output_path, 'output.tif'),\
                    'half_basin':'TEMPORARY_OUTPUT',\
                    'length_slope':'TEMPORARY_OUTPUT',\
                    'slope_steepness':'TEMPORARY_OUTPUT',\
                    'tci':'TEMPORARY_OUTPUT',\
                    'spi':'TEMPORARY_OUTPUT',\
                    'GRASS_REGION_PARAMETER':None,\
                    'GRASS_REGION_CELLSIZE_PARAMETER':0,\
                    'GRASS_RASTER_FORMAT_OPT':'',\
                    'GRASS_RASTER_FORMAT_META':''})
    
    return watershed_raster['stream']

def cutraster(raster,polygon,path_dict):  #cut raster by polygon
    output_path = createoutputpathascii(path_dict,'cut_raster')
    cut_raster = processing.run("gdal:cliprasterbymasklayer",\
                    {'INPUT':raster,\
                    'MASK':polygon,\
                    'NODATA':None,\
                    'ALPHA_BAND':False,\
                    'CROP_TO_CUTLINE':True,\
                    'KEEP_RESOLUTION':False,\
                    'OPTIONS':'',\
                    'DATA_TYPE':0,\
                    'EXTRA':'',\
                    'OUTPUT':os.path.join(output_path, 'output.tif')})
    
    return cut_raster['OUTPUT']

def  rastertopolygon(raster,path_dict): #convert raster to polygon
    output_path = createoutputpathascii(path_dict,'raster_to_polygon')
    raster_to_polygon = processing.run("gdal:polygonize",\
                    {'INPUT':raster,\
                    'BAND':1,\
                    'FIELD':'DN',\
                    'EIGHT_CONNECTEDNESS':False,\
                    'EXTRA':'',\
                    'OUTPUT':os.path.join(output_path, 'output.shp')})
    
    raster_to_polygon_layer = raster_to_polygon['OUTPUT']
    return raster_to_polygon_layer

def polygontoline(polygons,path_dict): #convert polygon to line
    output_path = createoutputpathascii(path_dict,'polygon_to_line')
    polygon_to_line = processing.run("native:dissolve",\
                    {'INPUT':polygons,\
                    'FIELD':[],\
                    'SEPARATE_DISJOINT':False,\
                    'OUTPUT':os.path.join(output_path, 'output.shp')})

    return polygon_to_line['OUTPUT']

def clipfields(fields, extent, path_dict): #extract layer part by extent
    output_path = createoutputpathascii(path_dict,'clip_fields')

    cliped_fields = processing.run("native:extractbyextent", {
        'INPUT': fields,
        'EXTENT':extent,
        'CLIP': False,
        'OUTPUT': os.path.join(output_path, 'output.shp')
    })
    return cliped_fields['OUTPUT']


def dissolvefields(fields, path_dict): #dissolve layer polygons, because of the overlapping
    output_path = createoutputpathascii(path_dict,'dissolve_fields')
    dissolve = processing.run("native:dissolve", {
        'INPUT': fields,
        'FIELD': [],
        'OUTPUT': os.path.join(output_path, 'output.shp')
    })

    return dissolve['OUTPUT']


### forest_roads.py 
 
def perpendicularline(vector, path_dict,angle): #create perpendicular line
    output_path = createoutputpathascii(path_dict,'perpendicular_line')
    s = f'extend (make_line ($geometry,project($geometry,2.5,radians("angle"-{angle}))),2.5,0)'
    perpendicular_line = processing.run("native:geometrybyexpression", {
        'INPUT': vector,
        'OUTPUT_GEOMETRY': 1,
        'WITH_Z': False,
        'WITH_M': False,
        #'EXPRESSION': 'extend (make_line ($geometry,project($geometry,2.5,radians("angle"-60))),2.5,0)',
        'EXPRESSION': s,
        'OUTPUT': os.path.join(output_path, 'output.gpkg')
    })

    return perpendicular_line['OUTPUT']

def finalperpendicularline(vector, path_dict,angle): #create perpendicular line
    output_path = path_dict
    random_prefix = ''.join(random.choices(string.ascii_letters + string.digits, k=10)) # 10char ascii random string
    s = f'extend (make_line ($geometry,project($geometry,2.5,radians("angle"-{angle}))),2.5,0)'
    perpendicular_line = processing.run("native:geometrybyexpression", {
        'INPUT': vector,
        'OUTPUT_GEOMETRY': 1,
        'WITH_Z': False,
        'WITH_M': False,
        #'EXPRESSION': 'extend (make_line ($geometry,project($geometry,2.5,radians("angle"-60))),2.5,0)',
        'EXPRESSION': s,
        'OUTPUT': os.path.join(output_path, random_prefix + 'output.gpkg')
    })

    return perpendicular_line['OUTPUT']

def separatelines(vector, path_dict): #separate lines
    output_path = createoutputpathascii(path_dict,'separated_lines')

    separate_lines = processing.run("native:splitvectorlayer", {
        'INPUT': vector,
        'FIELD': 'ID',
        'OUTPUT': os.path.join(output_path, 'separated_lines_folder')
    })

    return separate_lines['OUTPUT'] # return a folder with separated lines


def convertprojection(vector, path_dict): #convert projection
    output_path = createoutputpathascii(path_dict,'converted_projection')

    convert_projection = processing.run("native:reprojectlayer", {
        'INPUT': vector,
        'TARGET_CRS': 'EPSG:5514',
        'OUTPUT': os.path.join(output_path, 'output.shp')
    })

    return convert_projection['OUTPUT']

def pointsalongline1m(vector,path_dict): #sample point along vector line 
    output_path = path_dict
    random_prefix = ''.join(random.choices(string.ascii_letters + string.digits, k=10)) # 10char ascii random string

    points = processing.run("native:pointsalonglines",\
                   {'INPUT':vector,\
                    'DISTANCE':1,\
                    'START_OFFSET':0,\
                    'END_OFFSET':0,\
                    'OUTPUT':os.path.join(output_path, random_prefix + 'output.gpkg')})
    points_layer = points['OUTPUT']
    return points_layer

def pointsalonglinecustom(vector,path_dict,len): #sample point along vector line 
    output_path = path_dict
    random_prefix = ''.join(random.choices(string.ascii_letters + string.digits, k=10)) # 10char ascii random string
    points = processing.run("native:pointsalonglines",\
                   {'INPUT':vector,\
                    'DISTANCE':len,\
                    'START_OFFSET':0,\
                    'END_OFFSET':0,\
                    'OUTPUT':os.path.join(output_path,random_prefix + 'output.gpkg')})
    points_layer = points['OUTPUT']
    return points_layer

def rastersampling(raster, vector, path_dict): #sample raster by vector
    output_path = path_dict
    random_prefix = ''.join(random.choices(string.ascii_letters + string.digits, k=10)) # 10char ascii random string
    sampled_raster = processing.run("native:rastersampling",\
                   {'INPUT':vector,\
                    'RASTERCOPY':raster,\
                    'COLUMN_PREFIX':'ELEV_',\
                    'OUTPUT':os.path.join(output_path, random_prefix +'output.gpkg')})
    
    return sampled_raster
