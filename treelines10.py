from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsProcessingLayerPostProcessorInterface
from qgis.core import QgsProcessingParameterFolderDestination
from qgis.core import QgsProject
from qgis.core import QgsVectorLayer, QgsSymbol, QgsSingleSymbolRenderer
from qgis.core import QgsVectorFileWriter

from PyQt5.QtGui import QColor  # Import QColor from PyQt5
from datetime import datetime

import processing
#import pandas as pd
import geopandas as gpd
import numpy as np
import os 
import time
import sys
import random
import string



class IsoTreelinesAlgo(QgsProcessingAlgorithm):
 
    def name(self):
        return 'treelines9'
 
    def displayName(self):
        return 'Tree lines'
 
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
            QgsProcessingParameterFeatureSink(
                'output', 'output', 
                type=QgsProcessing.TypeVectorPolygon
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
        isolines = {}
        distancebetweenlines = {}
        paths = {}
        
        # import created tool scripts
        sys.path.append(parameters['mainfolder'])
        #print(parameters['mainfolder'])
        import qgis_tools as qtool 

        # Add the folder to the Python path
        #sys.path.append(parameters['mainfolder'])
        #from qgis_tools import simplifycontour, createoutputpathdir, createoutputpathascii, contourelevation, pointsalongline, deletecolumns, calculateshortestlines, buffering

        #define dictionary paths 
        paths['default'] = parameters['mainfolder']

        paths['tempfiles'] = qtool.createoutputpathdir(paths['default'],'temp_files') 

        paths['contours'] = qtool.createoutputpathdir(paths['tempfiles'],'contours')    
        paths['pointsalongline'] = qtool.createoutputpathdir(paths['tempfiles'],'points_along_line')
        paths['deletecomlumn'] = qtool.createoutputpathdir(paths['tempfiles'],'delete_column')
        paths['buffer'] = qtool.createoutputpathdir(paths['tempfiles'],'buffer_zones')
        paths['simplifygeom'] = qtool.createoutputpathdir(paths['tempfiles'],'simplifyed_geometries')
        paths['shorteslines'] = qtool.createoutputpathdir(paths['tempfiles'],'shortest_lines')






        #delete files in temp_folder
        #folder_path = 'C:/Users/jakub/Desktop/treelines/temp_files'
        #remove_files_in_folder(folder_path)

        # statistic of raster layer to get the highest point for alg start 
        dem_data = processing.run("native:rasterlayerstatistics",\
                        {'INPUT':parameters['inputr'],\
                        'BAND':1,\
                        'OUTPUT_HTML_FILE':'TEMPORARY_OUTPUT'})
        dem_max = dem_data['MAX'] - 1 # maximal value of input raster minus 1m 
        dem_min = dem_data['MIN']   # minimal value of input raster minus 1m 
        iso_a = '-fl '
        iso_b = str(dem_max)
        isoline_elevation = ''.join([iso_a,iso_b])
        
        #create output folder with file shp
        output_path = qtool.createoutputpathdir(paths['contours'],'max_contour')



        #isoline in defined elevation 
        outputs['Izolinie1'] = processing.run("gdal:contour",\
        #results = processing.run("gdal:contour",\
            {'INPUT':parameters['inputr'],\
            'BAND':1,\
            'INTERVAL':10,\
            'FIELD_NAME':'ELEV',\
            'CREATE_3D':False,\
            'IGNORE_NODATA':False,\
            'NODATA':None,\
            'OFFSET':0,\
            'EXTRA':isoline_elevation,\
            'OUTPUT':os.path.join(output_path, 'output.shp')})
        results['Output1'] = outputs['Izolinie1']['OUTPUT'] # results is and OUTPUT in Izolinie_1
        isolines['isoline1'] = outputs['Izolinie1']['OUTPUT'] # save for following distance statistics
        # Access the temporary output layer using the key defined in the parameters dictionary
        #output_layer1 = results['Output1']

        # Create a QgsVectorLayer object from the output layer
        vector_layer = QgsVectorLayer(os.path.join(output_path, 'output.shp'), "Contour", "ogr")

        # Add the vector layer to the current project
        #QgsProject.instance().addMapLayer(vector_layer)
        print(results)

        ####### start loops from here

        elev_new = dem_max - 5 # pocatecni nastrel nove hodnoty pro isolinii pro cycklus
        dis_tree_line = 200
        slope_new = 0 # flat land

        # Define the three number intervals using numpy arrays
        dist_max = 130 # initial maximal distance for tree lines in low slope land
        dist_min = 110 # initial minimal distance for tree lines in low slope land


        while elev_new > dem_min+5: # condition to create new tree lines to the land lowest area
            while dis_tree_line > dist_max or dis_tree_line < dist_min:
                iso_b = str(elev_new)
                #isoline in defined elevation for distance comparison
                isoline_elevation = ''.join([iso_a,iso_b])
                
                #calculate isoline2 contour at defined elevation
                isolines['isoline2'] = outputcountour = qtool.contourelevation(parameters['inputr'],paths['contours'],isoline_elevation) # input raster, path to contour folder, elevation for calculation
                # Create a QgsVectorLayer object from the output layer
                vector_layer = QgsVectorLayer(outputcountour, "Contour", "ogr")   
            
                #create output folder with file shp
                layer_name = 'sampledpoints1' #identification in name of folder
                output_path = qtool.createoutputpathascii(paths['contours'],layer_name)

                #create a points with defined span on the vector line for distance comparison on isoline 1
                results['output3'] = qtool.pointsalongline(isolines['isoline1'],paths['pointsalongline'])

                #edit a atribute table of points layer from isoline1
                results['output4'] = qtool.deletecolumns(results['output3'],paths['deletecomlumn'])

                #output_layer2 = QgsVectorLayer(results['Output3'], "Contour", "ogr")  #bodova vrstva 
                #QgsProject.instance().addMapLayer(output_layer2)

                #create a points with defined span on the vector line for distance comparison on isoline 2
                results['output5'] = qtool.pointsalongline(isolines['isoline2'],paths['pointsalongline'])

                #edit a atribute table of points layer from isoline2
                results['output6'] = qtool.deletecolumns(results['output5'],paths['deletecomlumn'])


                # calculate shortest lines between isolines

                results['output7'],output_path = qtool.calculateshortestlines(results['output4'],results['output6'],paths['shorteslines']) #shortest lines 

                # Load the generated shapefile into the map
                #layer = QgsVectorLayer(results['output7'], 'Shortest Lines', 'ogr')
                #QgsProject.instance().addMapLayer(layer)

                dbffile = os.path.join(output_path, 'output.dbf') # load the atribute table
                gdf = gpd.read_file(dbffile) # read the atribute table

                # Compute the difference between the 1st and 2nd column z-axis difference
                dif = gdf["ELEV"] - gdf["ELEV_2"]

                # Square the difference
                dif_squared = dif ** 2
    
                # Calculate the 3D distance using the pythagoras formula
                gdf["result"] = np.sqrt(gdf["distance"]**2 - dif_squared)
                dis_tree_line = round(gdf["result"].mean()) # get the mean value for new countour

                #calculate slope 
                slope_array = np.divide(dif,gdf["distance"])
                slope = np.mean(slope_array)
                #print(slope_array)
                print(dis_tree_line)
                print(slope)
                #time.sleep(1)

                if slope < 0.7:
                    dist_max = 125 
                    dist_min = 115
                elif slope > 0.7 and slope < 0.12:
                    dist_max = 65
                    dist_min = 55
                elif slope >0.12:
                    dist_max = 45
                    dist_min = 35

                # decision making
                if dis_tree_line > dist_max: 
                    elev_new = elev_new + 0.1
                elif dis_tree_line < dist_min: 
                    elev_new = elev_new - 0.1

                ###layer = QgsVectorLayer(results['Output4'], 'Layer Name', 'ogr')
                ###QgsProject.instance().addMapLayer(layer)
            else:
                print('layer complete')
                elev_new = elev_new - 5
                dis_tree_line = 200 # just a constant for new iteration 
                isolines['isoline1'] = isolines['isoline2'] # swiching the targert and source countour
                ##QgsProject.instance().addMapLayer(vector_layer)  
                print(elev_new)

                simple_layer = qtool.simplifycontour(vector_layer,paths['simplifygeom'])
                #QgsProject.instance().addMapLayer(simple_layer)

                # obal_layer,layer = qtool.buffering(simple_layer,paths['buffer']) # create a buffer zone aroung vector line 


                # Set the color of the polygon
                #symbol = QgsSymbol.defaultSymbol(obal_layer.geometryType())
                #symbol.setColor(QColor(0, 153, 0))  # Set the color to green, change values accordingly
                #symbol.setOpacity(0.7)  # Set the opacity, if needed

                # Create a renderer
                #renderer = QgsSingleSymbolRenderer(symbol)
                #obal_layer.setRenderer(renderer)

                # Add the layer to the project
                layer = QgsVectorLayer(simple_layer, 'Lesni Pas', 'ogr')
                
                layer.loadNamedStyle( os.path.join(paths['default'], 'green_dot.qml'))
                
                
                
                # Check if layer is valid
                if not layer.isValid():
                    print("Layer failed to load!")
                else:
                    # Add layer to QGIS
                    QgsProject.instance().addMapLayer(layer)



        return results
    
    
