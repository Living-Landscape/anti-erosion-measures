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
from geopandas import GeoDataFrame
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
import shutil



class IsoTreelinesAlgo(QgsProcessingAlgorithm):
 
    def name(self):
        return 'forest roads'
 
    def displayName(self):
        return 'forest roads'
 
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
                'mainfolder', 'Choose folder with scripts and outputdata destination',defaultValue=os.path.join('C:\\', 'Users', 'Kuba', 'AppData', 'Roaming', 'QGIS', 'QGIS3', 'profiles', 'default', 'processing', 'scripts', 'anti-erosion-measures'), 
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
        destination_dir_points = qtool.createoutputpathdir(paths['tempfiles'],'points')

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
                
                elev = gdf['ELEV_1'].to_numpy()
                distance = gdf['distance'].to_numpy()
                dx_distances = np.diff(distance)  # 1m
                dz_elevs = np.diff(elev)  # elevation difference between points i and i-1
                dd3_distances = np.sqrt(dx_distances**2 + dz_elevs**2)  # 3D distance between points i and i-1
                dslopes = dz_elevs/dx_distances  # slope between points i and i-1
                
                start_i = 0
                
                # loop over the rows
                for j in range(1,rows):
                    for i in range(start_i+1,start_i+51):
                        if i == rows:
                            break
                        dx_distance = dx_distances[i-1]  # 1m
                        dz_elev = dz_elevs[i-1]# elevation difference between points i and i-1
                        
                        d3_distance = dd3_distances[start_i:i].sum()# add the 3D distance to the total 3d distance

                        
                        # segment_slope = np.append(segment_slope,dslope)  # add the slope to the array
                        segment_slope = dslopes[start_i:i]  # add the slope to the array
                     # calculate the average slope
                        slope = abs(np.mean(segment_slope))

                        slope_ix = (dz_elev - dz_elevs[start_i])/(dx_distance - dx_distances[start_i]) #slope between the first point and the current point

                        #print('actual elev', gdf.at[i, 'ELEV_1'],'///','elev_ini',elev_ini,'///','actual distance', gdf.at[i, 'distance'],'///','distance_ini',distance_ini)

                        #print('3d_distance=', d3_distance,'///','slope=',slope)

                        #time.sleep()  # Pause for 1 second

                        
                        if d3_distance > 18 and slope > 0.16: # (slope_ix > 0.16 or slope > 0.16):
                            
                            start_i = i
                            print('point1 was created')
                            forest_points = pd.concat([forest_points, gdf.iloc[i:i+1]], ignore_index=True)

                            # Create a new GeoDataFrame for the current point
                            current_point = GeoDataFrame(gdf.iloc[i:i+1], crs=gdf.crs)
                            # Define the output file path
                            output_file_path = os.path.join(destination_dir_points, "point_{}.gpkg".format(i))
                            # Save the current point to a GeoPackage file
                            current_point.to_file(output_file_path, driver="GPKG")

                        elif d3_distance > 23 and slope > 0.14: #  (slope_ix > 0.14 or slope > 0.14):
                            
                            start_i = i
                            print('point2 was created')

                            forest_points = pd.concat([forest_points, gdf.iloc[i:i+1]], ignore_index=True)
                            # Create a new GeoDataFrame for the current point
                            current_point = GeoDataFrame(gdf.iloc[i:i+1], crs=gdf.crs)
                            # Define the output file path
                            output_file_path = os.path.join(destination_dir_points, "point_{}.gpkg".format(i))
                            # Save the current point to a GeoPackage file
                            current_point.to_file(output_file_path, driver="GPKG")                        
                            
                        elif d3_distance > 27 and slope > 0.12: #  (slope_ix > 0.12 or slope > 0.12):
                            
                            start_i = i
                            print('point3 was created')

                            forest_points = pd.concat([forest_points, gdf.iloc[i:i+1]], ignore_index=True)
                            # Create a new GeoDataFrame for the current point
                            current_point = GeoDataFrame(gdf.iloc[i:i+1], crs=gdf.crs)
                            # Define the output file path
                            output_file_path = os.path.join(destination_dir_points, "point_{}.gpkg".format(i))
                            # Save the current point to a GeoPackage file
                            current_point.to_file(output_file_path, driver="GPKG")

                        elif d3_distance > 32 and slope > 0.10:  # (slope_ix > 0.10 or slope > 0.10):
                        
                            start_i = i
                            print('point4 was created')
                            forest_points = pd.concat([forest_points, gdf.iloc[i:i+1]], ignore_index=True)

                            # Create a new GeoDataFrame for the current point
                            current_point = GeoDataFrame(gdf.iloc[i:i+1], crs=gdf.crs)
                            # Define the output file path
                            output_file_path = os.path.join(destination_dir_points, "point_{}.gpkg".format(i))
                            # Save the current point to a GeoPackage file
                            current_point.to_file(output_file_path, driver="GPKG")
    
                        elif d3_distance > 40 and slope > 0.08: # (slope_ix > 0.08 or slope > 0.08)
                        
                            start_i = i
                            print('point5 was created')
                            forest_points = pd.concat([forest_points, gdf.iloc[i:i+1]], ignore_index=True)

                            # Create a new GeoDataFrame for the current point
                            current_point = GeoDataFrame(gdf.iloc[i:i+1], crs=gdf.crs)
                            # Define the output file path
                            output_file_path = os.path.join(destination_dir_points, "point_{}.gpkg".format(i))
                            # Save the current point to a GeoPackage file
                            current_point.to_file(output_file_path, driver="GPKG")

                        elif d3_distance > 50 and  slope > 0.06: #  (slope_ix > 0.06 or slope > 0.06)
                        
                            start_i = i
                            print('point6 was created')
                            #print whole i row
                            #print(gdf.iloc[i])
                            # append the row to the forest points dataframe 
                            forest_points = pd.concat([forest_points, gdf.iloc[i:i+1]], ignore_index=True)

                            current_point = GeoDataFrame(gdf.iloc[i:i+1], crs=gdf.crs)
                            # Define the output file path
                            output_file_path = os.path.join(destination_dir_points, "point_{}.gpkg".format(i))
                            # Save the current point to a GeoPackage file
                            current_point.to_file(output_file_path, driver="GPKG")


                        elif d3_distance > 50 and (slope_ix < 0.06 or slope < 0.06): # maximum distance between points but without sufficient slope - shift the initial point by 1m
                            # gdf2.drop(i, inplace=True)
                            start_i = start_i + 1
                            break
                            #print('shifting')

                        # else: 
                        #     # smazay bod 
                        #     pass
                        #     # gdf2.drop(i, inplace=True)
                        #     #print('point was deleted') 
                    # print('start_i',start_i)
                    # print('i',i)
                    # print('rows',rows)
                    # print('d3_distance',d3_distance)   
                    # time.sleep(1)  # Pause for 1 second       
                    if i >= rows:
                        break
                    
        # Convert the DataFrame to a GeoDataFrame
        print('tablecolumnsnames',forest_points.columns)
        new_gdf = gpd.GeoDataFrame(forest_points, geometry='geometry')  # Replace 'geometry' with your actual geometry column

        # Save the new GeoDataFrame as a GPKG file
        save_path = os.path.join(paths['tempfiles'], 'filtered_points.gpkg')
        new_gdf.to_file(save_path, driver='GPKG')
        print('table',new_gdf)




        paths['perpendicularlines'] = qtool.createoutputpathdir(paths['tempfiles'],'perpendicular_line')
        paths['finallines'] = qtool.createoutputpathdir(paths['tempfiles'],'final_lines')
        #generate lines with angle 
        files = os.listdir(destination_dir_points)
        print('starting loop over selected points')
        # Loop over the files
        for file in files:
            # Check if the file is a geopackage file
            if file.endswith('.gpkg'):
                # Construct the full file path
                file_path = os.path.join(destination_dir_points, file)

                #generate lines with angle 
                angle_90_line = qtool.perpendicularline(file_path,paths['perpendicularlines'],90)
                angle_60_line = qtool.perpendicularline(file_path,paths['perpendicularlines'],60)
            
                points_90_line = qtool.pointsalonglinecustom(angle_90_line, paths['perpendicularlines'],4.9)
                points_60_line = qtool.pointsalonglinecustom(angle_60_line, paths['perpendicularlines'],4.9)

                sampled_90_lines = qtool.rastersampling(parameters['inputr'],points_90_line,paths['perpendicularlines'])
                sampled_60_lines = qtool.rastersampling(parameters['inputr'],points_60_line,paths['perpendicularlines'])

                # Load the geopackage data
                s90 = gpd.read_file(sampled_90_lines['OUTPUT'])
                s60 = gpd.read_file(sampled_60_lines['OUTPUT'])
                # calculate delta h 
                dhs90 = s90.at[0, 'ELEV_1_2'] - s90.at[1, 'ELEV_1_2']
                dhs60 = s60.at[0, 'ELEV_1_2'] - s60.at[1, 'ELEV_1_2']
                print('dhs90=',dhs90), print('dhs60=',dhs60)

                if dhs90 > 0.5 or dhs60 > 0.5:
                    fline = qtool.finalperpendicularline(file_path,paths['finallines'],60)
                else:
                    fline = qtool.finalperpendicularline(file_path,paths['finallines'],120)

        # Get a list of all GeoPackage files in the directory
        gpkg_files = [f for f in os.listdir(paths['finallines']) if f.endswith('.gpkg')]

        # Read the first file to initialize the GeoDataFrame
        gdf = gpd.read_file(os.path.join(paths['finallines'], gpkg_files[0]))

        # Loop over the rest of the files
        for file in gpkg_files[1:]:
            # Read the current file
            current_gdf = gpd.read_file(os.path.join(paths['finallines'], file))
            
            # Concatenate the current GeoDataFrame with the main GeoDataFrame
            gdf = gpd.pd.concat([gdf, current_gdf])          

        # Save the GeoDataFrame to a new GeoPackage file
        gdf.to_file(os.path.join(paths['finallines'], 'all_lines.gpkg'), driver='GPKG')

        #generate penperdicular lines 
        results['penperdicularlines'] = qtool.perpendicularline(save_path,paths['tempfiles'],60) # last value is angle of line

        #generate buffer zone 
        results['terawave'] = qtool.buffering(results['penperdicularlines'],1,paths['tempfiles'])


        layer = QgsVectorLayer(results['terawave'][1], 'Lesni Pas', 'ogr')

        # Check if layer is valid
        if not layer.isValid():
            print("Layer failed to load!")
        else:
            # Add layer to QGIS
            QgsProject.instance().addMapLayer(layer)
        
        
        shutil.rmtree(paths['tempfiles'],ignore_errors=True)
        
                
        return results
    

 