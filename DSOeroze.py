from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsProcessingLayerPostProcessorInterface
from qgis.core import QgsProcessingParameterFolderDestination
from qgis.core import QgsProject
from qgis.core import QgsRasterLayer, QgsSymbol, QgsSingleSymbolRenderer
from qgis.core import QgsVectorFileWriter
from qgis.core import QgsMapSettings, QgsVectorLayer, QgsRectangle, QgsLayoutExporter
from qgis.core import QgsProcessingParameterBoolean
from qgis.core import QgsVectorFileWriter, QgsFeatureRequest
from shapely.geometry import Point

from PyQt5.QtGui import QColor  # Import QColor from PyQt5
from datetime import datetime
from PIL import Image
from osgeo import gdal, osr

import processing
#import pandas as pd
import geopandas as gpd
import numpy as np
import os 
import time
import sys
import numpy as np
import shutil

class IsoTreelinesAlgo(QgsProcessingAlgorithm):
    CHECKBOX_PARAMETER = 'CHECKBOX_PARAMETER'  # Define the checkbox parameter
    def name(self):
        return 'Zatravnění drah soustředěného odtoku'
 
    def displayName(self):
        return 'Zatravnění drah soustředěného odtoku'
 
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
            QgsProcessingParameterNumber(
                'watershedbasins','Minimum size of an exterior watershed basin in cells', 
                type=QgsProcessingParameterNumber.Integer,  # Type of the number 
                minValue=5,  # Minimum allowed value
                maxValue=1000000,  # Maximum allowed value
                defaultValue=30000  # Default value (optional)
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.CHECKBOX_PARAMETER,
                'Calculate Watershed ?',
                defaultValue=False
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                'inputwatershed','Processed/Cutted watershed', 
                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                'limit_slope','minimal slope for DSO segment, lower slope segments will be filtered out',
                type=QgsProcessingParameterNumber.Double,  # Type of the number 
                minValue=0,  # Minimum allowed value
                maxValue=1,  # Maximum allowed value
                defaultValue=0.05 # Default value (optional)   limits['slope']
            )
        )

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                'inputv','Polygon to cut fields', 
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                'DSObuffer','size of the buffer around the DSO segments in meters', 
                type=QgsProcessingParameterNumber.Integer,  # Type of the number 
                minValue=1,  # Minimum allowed value
                maxValue=100,  # Maximum allowed value
                defaultValue=15  # Default value (optional)
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
        paths['gpkgs'] = qtool.createoutputpathdir(paths['tempfiles'],'separated_points')
        limit_slope = self.parameterAsDouble(parameters, 'limit_slope', context)

        # Define the destination path for filtered raster files with greater slope
        dest_path = qtool.createoutputpathdir(paths['tempfiles'],'filtered_raster')

        # Get the value of the checkbox
        checkbox_value = self.parameterAsBool(parameters, self.CHECKBOX_PARAMETER, context)

        raster_layer = self.parameterAsRasterLayer(parameters, 'inputr', context)

        extent = raster_layer.extent()
        xmin = extent.xMinimum()
        xmax = extent.xMaximum()
        ymin = extent.yMinimum()
        ymax = extent.yMaximum()
        extent = '{},{},{},{}'.format(xmin, xmax, ymin, ymax)
        print(extent)

        if checkbox_value:
            
            #create depresionless DEM
            results['depresionless_dem'] = qtool.filterDEM(parameters['inputr'],paths['tempfiles'])
            print('depresionless_dem created')

            #calculate the watershed
            results['watershed'] = qtool.watershed(results['depresionless_dem'],paths['tempfiles'],parameters['watershedbasins']) 
            print('watershed created')

        else: 
            #for not calculating watershed 
            results['watershed'] = parameters['inputwatershed']

        #cut the fields with the raster layer extent ""def clipfields(fields, raster, path_dict):""
        results['clipedfields']= qtool.clipfields(parameters['inputv'],extent,paths['tempfiles'])
        print('clipedfields created')

        #dissolve the fields ""def dissolvefields(fields, path_dict):""
        results['dissolvedfields'] = qtool.dissolvefields(results['clipedfields'],paths['tempfiles'])
        print('dissolvedfields created')

        #cut the watershed with the field polygon ""def cutraster(raster,polygon,path_dict):""
        results['cuttedwatershed'] = qtool.cutraster(results['watershed'],results['dissolvedfields'],paths['tempfiles'])
        print('cuttedwatershed created')

        #raster pixels to points
        results['rasterpixels'] = qtool.rasterpixelstopoints(results['cuttedwatershed'],paths['tempfiles'])

        gdf = gpd.read_file(results['rasterpixels'])
        print('gdf',gdf)
        # Get unique values in the "VALUE" column
        unique_values = gdf['VALUE'].unique()

        # For each unique value...
        for value in unique_values:
            # Create a new GeoDataFrame that only contains points with that value
            new_gdf = gdf[gdf['VALUE'] == value]

            # Define the filename. Make sure it's a string and doesn't contain any invalid characters
            filename = str(value).replace('/', '_').replace('\\', '_')

            # Define the full path to the file
            filepath = os.path.join(paths['gpkgs'], '{}.gpkg'.format(filename))

            # Save the new GeoDataFrame to a separate GeoPackage file
            new_gdf.to_file(filepath, driver='GPKG')

        # Get a list of all the GeoPackage files in the output directory
        gpkg_files = [f for f in os.listdir(paths['gpkgs']) if f.endswith('.gpkg')]
        for gpkg_file in gpkg_files:
            # Load the GeoPackage file as a vector layer
            layer = QgsVectorLayer(os.path.join(paths['gpkgs'], gpkg_file), gpkg_file, 'ogr')

            #sample the raster acording to the DEM raster 
            sampled_points= qtool.rastersampling(parameters['inputr'],layer,paths['tempfiles'])
            
            gdf = gpd.read_file(sampled_points['OUTPUT'])

            # Assume 'gdf' is your GeoDataFrame and it has a 'geometry' column that contains the points
            points = gdf['geometry'].tolist()
            elev_diff = gdf['ELEV_1'].tolist()

            # Select every 10th point
            points = points[::10]
            elev_diff = elev_diff[::10]
            # Calculate the distance and elevetion difference between consecutive points

            distances = [points[i].distance(points[i + 1]) for i in range(len(points) - 1)]
            elevations = [abs(elev_diff[i] - elev_diff[i + 1]) for i in range(len(elev_diff) - 1)]

            slopes = [elevations[i] / distances[i] for i in range(len(elevations))]
            avg_slope = np.mean(slopes) 
            #print('slopes',slopes)
            print('avg_slope',avg_slope)
            #print('distance',distances)
            # Now 'distances' is a list of distances between every 10th point
            #print(distances)
            # If the average slope is less than the threshold...
            # If the average slope is less than the threshold...
            if avg_slope > limit_slope:
                

                # Copy the file
                shutil.copy(os.path.join(paths['gpkgs'], gpkg_file), dest_path)

        import pandas as pd

        # Get a list of all files in the directory
        files = os.listdir(dest_path)

        # Initialize an empty list to store the GeoDataFrames
        layers = []

        # Loop through the files
        for file in files:
            # Create the full file path
            file_path = os.path.join(dest_path, file)

            # Read the file into a GeoDataFrame
            layer = gpd.read_file(file_path)

            # Add the GeoDataFrame to the list
            layers.append(layer)

            # Concatenate all GeoDataFrames into one
            all_layers = pd.concat(layers, ignore_index=True)

        # Save the all_layers GeoDataFrame to a file
        filtered_points_DSO = os.path.join(dest_path, 'all_layers.gpkg') # filtered_points_DSO is the path to gpkg file 
        all_layers.to_file(filtered_points_DSO, driver='GPKG') # save the data

        #polygonize the raster 
        #results['polygonizedwatershed'] = qtool.rastertopolygon(results['cuttedwatershed'],paths['tempfiles'])
        #print('polygonizedwatershed created')

        #polygon to line   
        #results['linedpolygon'] = qtool.polygontoline(results['polygonizedwatershed'],paths['tempfiles'])
        #print('linedpolygon created')

        #buffer the DSO 
        results['bufferedpoints'] = qtool.buffering(filtered_points_DSO,parameters['DSObuffer'],paths['tempfiles'])
        print('bufferedlines created')

        #dissolve the fields ""def dissolvefields(fields, path_dict):""
        results['dissolvedpolygonpoints'] = qtool.dissolvefields(results['bufferedpoints'][1],dest_path)
        print('dissolvedfields created')        
        


        # add layer to qgis
        layer = QgsVectorLayer(results['dissolvedpolygonpoints'], "DSO_grass", "ogr") # [1] is the second element in OUTPUT dictionary
        
        
        # Check if layer is valid
        if not layer.isValid():
            print("Layer failed to load!")
        else:
            # Add layer to QGIS
            QgsProject.instance().addMapLayer(layer)



            






        return results
    
