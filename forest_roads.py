from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsProcessingLayerPostProcessorInterface
from qgis.core import QgsProcessingParameterFolderDestination
from qgis.core import QgsProject, edit
from qgis.core import QgsRasterLayer, QgsSymbol, QgsSingleSymbolRenderer
from qgis.core import QgsVectorFileWriter, QgsPoint, QgsGeometry, QgsFeature
from qgis.core import QgsMapSettings, QgsVectorLayer, QgsRectangle, QgsLayoutExporter

from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
from qgis.utils import iface

from qgis.core import QgsField



from PyQt5.QtGui import QColor  # Import QColor from PyQt5
from datetime import datetime
from PIL import Image
from osgeo import gdal, osr

import processing
import pandas as pd
import geopandas as gpd
import numpy as np
import os 
import time
import sys
import numpy as np
import inspect
import math 




class IsoTreelinesAlgo(QgsProcessingAlgorithm):
 
    def name(self):
        return 'DSO'
 
    def displayName(self):
        return 'DSO'
 
    def group(self):
        return 'RAGO scripts'
 
    def groupId(self):
        return 'ragoscripts'
 
    def createInstance(self):
        return type(self)()
         
     #dialog to select inputs and outputs    
    def initAlgorithm(self, config=None):
        '''self.addParameter(
            QgsProcessingParameterVectorLayer(
                'inputv', 'Vstupní vektor', 
                types=[QgsProcessing.TypeVectorAnyGeometry]
            )
        )'''
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                'inputr', 'Choose input raster layer', 
            )
        )

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                'inputv',' Input tracks layer', 
            )
        )

        self.addParameter(
            QgsProcessingParameterFolderDestination(
                'mainfolder', 'Choose folder with scripts and outputdata destination',defaultValue=os.path.join('C:\\', 'Users', 'spravce', 'AppData', 'Roaming', 'QGIS', 'QGIS3', 'profiles', 'default', 'processing', 'scripts', 'anti-erosion-measures'), 
            )
            
        )


    
        
    def processAlgorithm(self, parameters, context, feedback):

        feedback = QgsProcessingMultiStepFeedback(1, feedback)
        results = {} #create a empty dictionary example outputs["res1"] = 42 save number 42 under name 
        outputs = {}
        sampledlines = {}
        paths = {}

        sys.path.append(parameters['mainfolder'])
        print(parameters['mainfolder'])
        import qgis_tools as qtool 

        paths['tempfiles'] = qtool.createoutputpathdir(parameters['mainfolder'],'temp_files')

        #change projection of input vector
        results['reprojected'] = qtool.convertprojection(parameters['inputv'],paths['tempfiles'])

        #separate vecotr layer 
        results['separated_lines'] = qtool.separatelines(results['reprojected'],paths['tempfiles'])

        print(results['separated_lines'])

        source_dir = results['separated_lines']
        destination_dir_a = qtool.createoutputpathdir(paths['tempfiles'],'sampled_lines')
        destination_dir_b = qtool.createoutputpathdir(paths['tempfiles'],'sampled_raster')
        destination_dir_c = qtool.createoutputpathascii(paths['tempfiles'],'remaining_points')

        
        # Create a new DataFrame to store the indexed rows based on algorithm
        forest_points = pd.DataFrame()
        print(type(forest_points))
        
        # Get a list of all files in the source directory
        files = os.listdir(source_dir)

        print('starting loop over short lines')
        # Loop over the files
        for file in files:
            # Check if the file is a geopackage file
            if file.endswith('.gpkg'):
                # Construct the full file path
                file_path = os.path.join(source_dir, file)
                
                #print(file_path)

                # points along lines
                results['points_along_lines'] = qtool.pointsalongline1m(file_path,destination_dir_a)
                results['sampled_raster1'] = qtool.rastersampling(parameters['inputr'],results['points_along_lines'],destination_dir_b)
                results['sampled_raster2'] = qtool.rastersampling(parameters['inputr'],results['points_along_lines'],destination_dir_c)

                # Define the file path
                file_path1 = results['sampled_raster1']['OUTPUT']
                file_path2 = results['sampled_raster2']['OUTPUT']

                # Load the geopackage file
                gdf = gpd.read_file(file_path1)
                gdf2 = gpd.read_file(file_path2)
                #print(file_path)
                #print(gdf)
                # set initial counters
                elev_ini = gdf.at[0, 'ELEV_1']
                distance_ini = gdf.at[0, 'distance']
                d3_distance = 0

                slope = 0
                rows = len(gdf)
                segment_slope = np.array([])
                
                # loop over the rows
                for i in range(1,rows):
                    dx_distance = gdf.at[i, 'distance']-gdf.at[i-1, 'distance']  # 1m
                    dz_elev = gdf.at[i, 'ELEV_1']- gdf.at[i-1, 'ELEV_1'] # elevation difference between points i and i-1
                    dd3_distance = math.sqrt(dx_distance**2 + dz_elev**2) # 3D distance between points i and i-1
                    d3_distance = d3_distance + dd3_distance  # add the 3D distance to the total 3d distance

                    dslope = dz_elev/dx_distance  # slope between points i and i-1 
                    segment_slope = np.append(segment_slope,dslope)  # add the slope to the array
                 # calculate the average slope
                    slope = abs(np.mean(segment_slope))

                    slope_ix = gdf.at[i, 'ELEV_1'] - elev_ini/gdf.at[i, 'distance'] - distance_ini #slope between the first point and the current point

                    #print('actual elev', gdf.at[i, 'ELEV_1'],'///','elev_ini',elev_ini,'///','actual distance', gdf.at[i, 'distance'],'///','distance_ini',distance_ini)

                    #print('3d_distance=', d3_distance,'///','slope=',slope)

                    #time.sleep()  # Pause for 1 second

                
                 # calculate the average slope
                    if i == rows:
                        print('end of the line')
                        break
                    elif d3_distance > 18 and slope > 0.16: # (slope_ix > 0.16 or slope > 0.16):
                        elev_ini = gdf.at[i, 'ELEV_1']
                        distance_ini = gdf.at[i, 'distance']
                        d3_distance = 0
                        slope = 0
                        segment_slope = np.array([])
                        print('point was created')

                    elif d3_distance > 23 and slope > 0.14: #  (slope_ix > 0.14 or slope > 0.14):
                        elev_ini = gdf.at[i, 'ELEV_1']
                        distance_ini = gdf.at[i, 'distance']
                        d3_distance = 0
                        slope = 0
                        segment_slope = np.array([])
                        print('point was created')
                        
                    elif d3_distance > 27 and slope > 0.12: #  (slope_ix > 0.12 or slope > 0.12):
                        elev_ini = gdf.at[i, 'ELEV_1']
                        distance_ini = gdf.at[i, 'distance']
                        d3_distance = 0
                        slope = 0
                        segment_slope = np.array([])
                        print('point was created')
                        
                    elif d3_distance > 32 and slope > 0.10:  # (slope_ix > 0.10 or slope > 0.10):
                        elev_ini = gdf.at[i, 'ELEV_1']
                        distance_ini = gdf.at[i, 'distance']
                        d3_distance = 0
                        slope = 0
                        segment_slope = np.array([])
                        print('point was created')
   
                    elif d3_distance > 40 and slope > 0.08: # (slope_ix > 0.08 or slope > 0.08)
                        elev_ini = gdf.at[i, 'ELEV_1']
                        distance_ini = gdf.at[i, 'distance']
                        d3_distance = 0
                        slope = 0
                        segment_slope = np.array([])
                        print('point was created')
        
                    elif d3_distance > 50 and  slope > 0.06: #  (slope_ix > 0.06 or slope > 0.06)
                        elev_ini = gdf.at[i, 'ELEV_1']
                        distance_ini = gdf.at[i, 'distance']
                        d3_distance = 0
                        slope = 0
                        segment_slope = np.array([])
                        print('point was created')
                        #print whole i row
                        #print(gdf.iloc[i])
                        # append the row to the forest points dataframe 
                        forest_points = pd.concat([forest_points, gdf.iloc[i:i+1]], ignore_index=True)
                        


                    elif d3_distance > 50 and (slope_ix < 0.06 or slope < 0.06): # maximum distance between points but without sufficient slope - shift the initial point by 1m
                        elev_ini = gdf.at[i-49, 'ELEV_1']
                        distance_ini = gdf.at[i-49, 'distance']
                        gdf2.drop(i, inplace=True)
                        #print('shifting')

                    else: 
                        # smazay bod 
                        gdf2.drop(i, inplace=True)
                        #print('point was deleted')

        # Convert the DataFrame to a GeoDataFrame
        print(forest_points.columns)
        new_gdf = gpd.GeoDataFrame(forest_points, geometry='geometry')  # Replace 'geometry' with your actual geometry column

        # Save the new GeoDataFrame as a GPKG file
        save_path = os.path.join(paths['tempfiles'], 'filtered_points.gpkg')
        new_gdf.to_file(save_path, driver='GPKG')
        print(new_gdf)

        
        #generate penperdicular lines 
        results['penperdicularlines'] = qtool.perpendicularline(save_path,paths['tempfiles'])

        #generate buffer zone 
        results['terawave'] = qtool.buffering(results['penperdicularlines'],1,paths['tempfiles'])


        layer = QgsVectorLayer(results['terawave'][1], 'Lesni Pas', 'ogr')

        # Check if layer is valid
        if not layer.isValid():
            print("Layer failed to load!")
        else:
            # Add layer to QGIS
            QgsProject.instance().addMapLayer(layer)
        

        return results
    

 