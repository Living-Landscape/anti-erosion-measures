from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsProcessingLayerPostProcessorInterface
from qgis.core import QgsProcessingParameterFolderDestination
from qgis.core import QgsProject
from qgis.core import QgsVectorLayer, QgsSymbol, QgsSingleSymbolRenderer
from qgis.core import QgsVectorFileWriter, QgsField
from PyQt5.QtCore import QVariant

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
import shutil



class IsoTreelinesAlgo(QgsProcessingAlgorithm):
 
    def name(self):
        return 'Stromové Linie'
 
    def displayName(self):
        return 'Stromové Linie'
 
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
                'inputv', 'Choose input vector layer of field blocks', 
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                'slopeA','Slope "A" for the maximal distance between tree lines',
                type=QgsProcessingParameterNumber.Double,  # Type of the number 
                defaultValue=0.07 # Default value (optional)  
            ) 
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                'distanceA','Treelines distance for slope "A" and smaller (slope B is between A and C)',
                type=QgsProcessingParameterNumber.Double,  # Type of the number 
                defaultValue=120 # Default value (optional)  
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                'distanceB','Treelines distance between slopes "A" and "C"',
                type=QgsProcessingParameterNumber.Double,  # Type of the number 
                defaultValue=60 # Default value (optional)  
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                'slopeC','Slope "C" for the minimum distance between tree lines',
                type=QgsProcessingParameterNumber.Double,  # Type of the number 
                defaultValue=0.12 # Default value (optional) 
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                'distanceC','Treelines distance for slope "C" and greater (slope B is between A and C)',
                type=QgsProcessingParameterNumber.Double,  # Type of the number 
                defaultValue=40 # Default value (optional)  
            )
        )

        self.addParameter(
            QgsProcessingParameterFolderDestination(
                'mainfolder', 'Choose folder with scripts and outputdata destination',defaultValue=os.path.join('C:\\', 'Users', 'jakub', 'AppData', 'Roaming', 'QGIS', 'QGIS3', 'profiles', 'default', 'processing', 'scripts', 'anti-erosion-measures'), 
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
        paths['mastertemp'] = qtool.createfolder(parameters['mainfolder'],'temporary files')

        paths['tempfiles'] = qtool.createoutputpathdir(paths['mastertemp'],'temp_files')

        paths['mainresults'] = qtool.createfolder(paths['tempfiles'],'main results')
        paths['calculations'] = qtool.createfolder(paths['tempfiles'],'calculations')


        paths['contours'] = qtool.createoutputpathdir(paths['calculations'],'contours')    
        paths['pointsalongline'] = qtool.createoutputpathdir(paths['calculations'],'points_along_line')
        paths['deletecomlumn'] = qtool.createoutputpathdir(paths['calculations'],'delete_column')
        paths['buffer'] = qtool.createoutputpathdir(paths['calculations'],'buffer_zones')
        paths['simplifygeom'] = qtool.createoutputpathdir(paths['calculations'],'simplifyed_geometries')
        paths['shorteslines'] = qtool.createoutputpathdir(paths['calculations'],'shortest_lines')
        paths['validlines'] = qtool.createoutputpathdir(paths['calculations'],'valiedated_lines')
        paths['offsetlines'] = qtool.createoutputpathdir(paths['calculations'],'offseted_lines')
        paths['treelines'] = qtool.createoutputpathdir(paths['calculations'],'created_treelines')
        paths['errorfiles'] = qtool.createoutputpathdir(paths['calculations'],'error_files')

        # Get the input raster layer to define layer extent
        raster_layer = self.parameterAsRasterLayer(parameters, 'inputr', context)

        extent = raster_layer.extent()
        xmin = extent.xMinimum()
        xmax = extent.xMaximum()
        ymin = extent.yMinimum()
        ymax = extent.yMaximum()
        extent = '{},{},{},{}'.format(xmin, xmax, ymin, ymax)
        print('extent of inpur raster layer',extent)




        #create a polygon from raster DEM layer to get landscape boundary
        results['rastercontour']= qtool.rastertopolygon(parameters['inputr'],paths['calculations'])
        print('clipedfields created')

        #dissolve the polygonized raster layer
        results['dissolvedraster'] = qtool.dissolvefields(results['rastercontour'],paths['calculations'])
        print('dissolvedfields created')

        #correct the dissolved raster layer
        results['correcteddissolvedfields'] = qtool.correctvector(results['dissolvedraster'],paths['calculations'])
        print('correcteddissolvedfields created')

        #cut the fields with the raster layer polygon to get the mask to cut the fileds one by one
        results['clipedfields'] = qtool.cutthefieldblocks(parameters['inputv'],results['correcteddissolvedfields'],paths['calculations'])
        print('clipedfields created')

        #dissolve the fields with too close boundaries
        results['dissolvedfields'] = qtool.dissolvefields(results['clipedfields'],paths['calculations'])
        print('dissolvedfields created')

        results['onepolygon'] = qtool.multipartpartpolygon(results['dissolvedfields'],paths['calculations'])
        

        def add_index_to_attributes(layer):
            # Add a new field to the layer
            
            provider = layer.dataProvider()
            provider.addAttributes([QgsField("IDX", QVariant.Int)])
            layer.updateFields()

            # Start editing the layer
            layer.startEditing()

            # Iterate over features and set the index value
            for i, feature in enumerate(layer.getFeatures()):
                feature["IDX"] = i
                layer.updateFeature(feature)
            # Commit changes
            layer.commitChanges()

        print(results['onepolygon'])
        layer = QgsVectorLayer(results['onepolygon'], "onepolygon", "ogr")
        results['indexedpolygon'] = add_index_to_attributes(layer)

        #separate vecotr layer, save all part to separate shp files
        results['separated_polygons'] = qtool.separatepolygons(results['onepolygon'],paths['calculations'])
        print(results['separated_polygons'])

        files = os.listdir(results['separated_polygons'])

        ### calculation for one input raster ### 
        counter = 0
        for file in files:
            try:
                print('soubor',file)
                poly_path = os.path.join(results['separated_polygons'],file)


                rasterpart = qtool.cutraster(parameters['inputr'],poly_path,paths['calculations']) # cut raster to the extent of the field

                # statistic of raster layer to get the highest point for alg start 
                dem_data = processing.run("native:rasterlayerstatistics",\
                                {'INPUT':rasterpart,\
                                'BAND':1,\
                                'OUTPUT_HTML_FILE':'TEMPORARY_OUTPUT'})
                dem_max = dem_data['MAX'] # maximal value of input partial raster
                

                if dem_max > 8000:  #skip the fields with high elevation
                    print('skipping field out of raster')
                    continue
                dem_min = dem_data['MIN']   # minimal value of input partial raster
                print('DEM_max',dem_max,'DEM_min',dem_min)

                #if abs(dem_min-dem_max) < 15:
                #    print('skipping field with low elevation difference')
                #    continue 
                #time.sleep(2)
                iso_a = '-fl '
                iso_b = str(dem_max-2)
                isoline_elevation = ''.join([iso_a,iso_b])
                
                #create output folder with file shp
                output_path = qtool.createoutputpathascii(paths['contours'],'max_contour')



                #isoline in defined elevation 
                outputs['in_isoline'] = qtool.contourelevation(rasterpart,paths['contours'],isoline_elevation)
                #results['Output1'] = outputs['Izolinie1']['OUTPUT'] # results is and OUTPUT in Izolinie_1
                isolines['isoline1'] = outputs['in_isoline'] # save for following distance statistics
                # Access the temporary output layer using the key defined in the parameters dictionary
                #output_layer1 = results['Output1']

                # Create a QgsVectorLayer object from the output layer
                #vector_layer = QgsVectorLayer(os.path.join(output_path, 'output.shp'), "Contour", "ogr")

                # Add the vector layer to the current project
                #QgsProject.instance().addMapLayer(vector_layer)
                #print(results)

                ####### start loops from here
                attemt_counter = 0
                elev_new = dem_max - 5 # pocatecni nastrel nove hodnoty pro isolinii pro cycklus
                dis_tree_line = 200
                file_check = 1
                slope_new = 0 # flat land

                # Define the three number intervals using numpy arrays
                dist_max = 130 # initial maximal distance for tree lines in low slope land
                dist_min = 110 # initial minimal distance for tree lines in low slope land


                while elev_new > dem_min: # condition to create new tree lines to the land lowest area
                    while (dis_tree_line > dist_max or dis_tree_line < dist_min) and elev_new > dem_min:

                        if file_check == 0: # file check == 0.... need new elevation, file_check == 1.... elevation is ok 
                            iso_a = '-fl '
                            iso_b = str(elev_new-5)
                            print('new elevation',elev_new)
                            elev_new = elev_new - 10
                            print('new elevation',elev_new)
                            print('filename',file)
                            isoline_elevation = ''.join([iso_a,iso_b])
                            #calculate new isoline1 contour at defined elevation
                            outputs['in_isoline'] = qtool.contourelevation(rasterpart,paths['contours'],isoline_elevation)
                            isolines['isoline1'] = outputs['in_isoline']
                            file_check = 1 # good file assumtion    
    
                        #isoline in defined elevation for distance comparison
                        iso_b = str(elev_new)
                        isoline_elevation = ''.join([iso_a,iso_b])
                        
                        #calculate isoline2 contour at defined elevation
                        isolines['isoline2'] = outputcountour = qtool.contourelevation(rasterpart,paths['contours'],isoline_elevation) # input raster, path to contour folder, elevation for calculation
                        # Create a QgsVectorLayer object from the output layer
                        vector_layer = QgsVectorLayer(outputcountour, "Contour", "ogr")   
                    
                        #create output folder with file shp
                        layer_name = 'sampledpoints1' #identification in name of folder
                        output_path = qtool.createoutputpathascii(paths['contours'],layer_name)

                        #create a points with defined span on the vector line for distance comparison on isoline 1
                        results['output3'] = qtool.pointsalongline(isolines['isoline1'],paths['pointsalongline'])

                        # contditions to minimum points to calculate distance 
                        layer = QgsVectorLayer(results['output3'], 'Layer Name', 'ogr')
                        if layer.featureCount() < 10:
                            print('not enough points to calculate distance')
                            file_check = 0
                            continue

                        #edit a atribute table of points layer from isoline1
                        results['output4'] = qtool.deletecolumns(results['output3'],paths['deletecomlumn'])

                        #output_layer2 = QgsVectorLayer(results['Output3'], "Contour", "ogr")  #bodova vrstva 
                        #QgsProject.instance().addMapLayer(output_layer2)

                        #create a points with defined span on the vector line for distance comparison on isoline 2
                        results['output5'] = qtool.pointsalongline(isolines['isoline2'],paths['pointsalongline'])

                        #edit a atribute table of points layer from isoline2
                        results['output6'] = qtool.deletecolumns(results['output5'],paths['deletecomlumn'])


                        # calculate shortest lines between isolines

                        results['output7'],output_path1 = qtool.calculateshortestlines(results['output4'],results['output6'],paths['shorteslines']) #shortest lines 
                        results['output7_2'],output_path2 = qtool.calculateshortestlines(results['output6'],results['output4'],paths['shorteslines']) #shortest lines 
                        # Load the generated shapefile into the map
                        #layer = QgsVectorLayer(results['output7'], 'Shortest Lines', 'ogr')
                        #QgsProject.instance().addMapLayer(layer)

                        dbffile = os.path.join(output_path1, 'output.dbf') # load the atribute table
                        dbffile2 = os.path.join(output_path2, 'output.dbf')

                        gdf = gpd.read_file(dbffile) # read the atribute table
                        gdf2 = gpd.read_file(dbffile2)

                        # Compute the difference between the 1st and 2nd column z-axis difference
                        dif = gdf["ELEV"] - gdf["ELEV_2"]
                        dif2 = gdf2["ELEV"] - gdf2["ELEV_2"]

                        # Square the difference
                        dif_squared = dif ** 2
                        dif_squared2 = dif2 ** 2
            
                        # Calculate the 3D distance using the pythagoras formula
                        gdf["result"] = np.sqrt(gdf["distance"]**2 - dif_squared)
                        gdf2["result"] = np.sqrt(gdf2["distance"]**2 - dif_squared2)

                        dis_tree_line = round(gdf["result"].mean()) # get the mean value for new countour
                        dis_tree_line2 = round(gdf2["result"].mean())

                        dis_tree_line = (dis_tree_line + dis_tree_line2)/2

                        
                        if dis_tree_line < dist_max and dis_tree_line > dist_min:
                            break
                        else:
                            #calculate slope 
                            slope_array = np.divide(dif,gdf["distance"])
                            slope = np.mean(slope_array)
                            #print(slope_array)
                            #time.sleep(0.5)
                            print('attempt counter',attemt_counter)
                            if attemt_counter > 30:
                                sense = 0.001
                                #time.sleep(0s.5)
                            elif attemt_counter > 15:
                                sense = 0.003
                            elif attemt_counter > 10:
                                sense = 0.007
                            elif attemt_counter > 5:
                                sense = 0.01
                            elif attemt_counter < 5:
                                sense = 0.02
                            
                            if slope < parameters['slopeA']:
                                dist_max = parameters['distanceA']+5 
                                dist_min = parameters['distanceA']-5
                                inc = (dis_tree_line - parameters['distanceA'])*sense
                            elif slope > parameters['slopeA'] and slope < parameters['slopeC']:
                                dist_max = parameters['distanceB']+5
                                dist_min = parameters['distanceB']-5
                                inc = (dis_tree_line - parameters['distanceB'])*sense
                            elif slope >parameters['slopeC']:
                                dist_max = parameters['distanceC']+5
                                dist_min = parameters['distanceC']-5
                                inc = (dis_tree_line - parameters['distanceC'])*sense

                            # decision making
                            attemt_counter = attemt_counter + 1    
                            inc = abs(inc)
                            print('inc',inc)
                            print('attemt_counter',attemt_counter)
                            print('slope',slope)
                            print('dis_tree_line',dis_tree_line)
                            print('dist_max',dist_max,'dist_min',dist_min)                        
                            print('old elevation',elev_new)
                            print('curent gpkg file',file)

                            #time.sleep(0.7)
                            if attemt_counter > 40:
                                dis_tree_line = dist_max/2 + dist_min/2
                            else:
                                if dis_tree_line > dist_max: 
                                    elev_new = elev_new + inc
                                elif dis_tree_line < dist_min: 
                                    elev_new = elev_new - inc
                            print('new elevation',elev_new)

                            ###layer = QgsVectorLayer(results['Output4'], 'Layer Name', 'ogr')
                            ###QgsProject.instance().addMapLayer(layer)
                    else:
                        print('layer complete')
                        time.sleep(0.5)
                        attemt_counter = 0
                        counter += 1
                        elev_new = elev_new - 5
                        dis_tree_line = 200 # just a constant for new iteration 
                        isolines['isoline1'] = isolines['isoline2'] # swiching the targert and source countour
                        ##QgsProject.instance().addMapLayer(vector_layer)  
                        #print(elev_new)

                        simple_layer = qtool.simplifycontour(vector_layer,paths['simplifygeom'])
                        #QgsProject.instance().addMapLayer(simple_layer)

                        valid_line = qtool.validatelayer(simple_layer,paths['validlines'])

                        simplified_layer1 = qtool.offsetline(valid_line, 30, paths['offsetlines'])
                        simplified_layer2 = qtool.offsetline(simplified_layer1, -30, paths['offsetlines'])

                        # Save the layer
                        filename = f"{counter}.gpkg"
                        #create a output path directory for the treelines 
                        
                        output_path = os.path.join(paths['treelines'], filename)
                        simplified_layer2_gdf = gpd.read_file(simplified_layer2)
                        simplified_layer2_gdf.to_file(output_path, driver='GPKG')
            except Exception as e:
                print(f"Error occurred: {e}")
                # save the problematic gpgk file to folder 
                current_error_file_path = os.path.join(results['separated_polygons'], file)
                error_files_path = os.path.join(paths['errorfiles'], file)
                shutil.copy(current_error_file_path, error_files_path)
                continue # Skip to the next iteration
        import pandas as pd

        # Get a list of all files in the directory
        files = os.listdir(paths['treelines'])

        # Initialize an empty list to store the GeoDataFrames
        layers = []

        # Loop through the files
        for file in files:
            # Create the full file path
            file_path = os.path.join(paths['treelines'], file)

            # Read the file into a GeoDataFrame
            layer = gpd.read_file(file_path)

            # Add the GeoDataFrame to the list
            layers.append(layer)

            # Concatenate all GeoDataFrames into one
            all_layers = pd.concat(layers, ignore_index=True)

        # Save the all_layers GeoDataFrame to a file
        output_path = os.path.join(paths['mainresults'], 'all_layers.gpkg')
        all_layers.to_file(output_path, driver='GPKG')

        # Create a new QgsVectorLayer
        layer = QgsVectorLayer(output_path, 'All Layers', 'ogr')

        # Check if layer is valid
        if not layer.isValid():
            print("Layer failed to load!")
        else:
            # Add layer to QGIS
            QgsProject.instance().addMapLayer(layer)
                    
                    #layer = QgsVectorLayer(simplified_layer2, 'Lesni Pas', 'ogr')

                    ## Check if layer is valid
                    #if not layer.isValid():
                    #    print("Layer failed to load!")
                    #else:
                    #    # Add layer to QGIS
                    #    QgsProject.instance().addMapLayer(layer)
                    

                    
                    #distance = 10
                    #obal_layer,layer = qtool.buffering(simple_layer,distance,paths['buffer']) # create a buffer zone aroung vector line 

                    # Add the layer to the project
                    
                    #layer = QgsVectorLayer(layer, 'Lesni Pas', 'ogr')

                    # Check if layer is valid
                    #if not layer.isValid():
                    #    print("Layer failed to load!")
                    #else:
                    #    # Add layer to QGIS
                    #    QgsProject.instance().addMapLayer(layer)
                    

        

        return results
