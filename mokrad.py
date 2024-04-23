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
import inspect




class IsoTreelinesAlgo(QgsProcessingAlgorithm):
    CHECKBOX_PARAMETER = 'CHECKBOX_PARAMETER'  # Define the checkbox parameter

    def name(self):
        return 'Mokřadní plochy okolo vodních toků'
 
    def displayName(self):
        return 'Mokřadní plochy okolo vodních toků'
 
    def group(self):
        return 'RAGO scripts'
 
    def groupId(self):
        return 'ragoscripts'
 
    def createInstance(self):
        return type(self)()
         
     #dialog to select inputs and outputs    
    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                'inputv', 'water streams (input vector layer)', 
                types=[QgsProcessing.TypeVectorAnyGeometry]
            )
        )

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                'kves','Consolidated ecosystem layer', 
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.CHECKBOX_PARAMETER,
                'Filter CEL ?',
                defaultValue=False
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                'buffersize','size of the buffer around the water stream in meters', 
                type=QgsProcessingParameterNumber.Integer,  # Type of the number 
                minValue=1,  # Minimum allowed value
                maxValue=100,  # Maximum allowed value
                defaultValue=15  # Default value (optional)
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
        paths = {}

        sys.path.append(parameters['mainfolder'])
        print(parameters['mainfolder'])
        import qgis_tools as qtool
        

        paths['tempfiles'] = qtool.createoutputpathdir(parameters['mainfolder'],'temp_files')

        # Get the value of the checkbox
        checkbox_value = self.parameterAsBool(parameters, self.CHECKBOX_PARAMETER, context)

        if checkbox_value:
            kves = os.path.join(parameters['mainfolder'],'KVES_Stredocesky','KVES_Stredocesky.shp')
            print('path to shp', kves)
            # Load the shapefile
            layer = QgsVectorLayer(kves, 'layer_name', 'ogr')
            print('layer',layer)
            # Get the attribute table
            provider = layer.dataProvider()
            print('provider',provider)
            # Get the index of the 2nd column
            fields = provider.fields()
            print('field',fields)
            second_column_index = fields.at(1).name()

            # Get all features in the attribute table
            features = layer.getFeatures()

            # The name you want to remove
            names_to_keep = ['Buèiny', 'Doubravy a dubohabøiny','Hospodáøské lesy jehliènaté','Hospodáøské lesy listnaté','Hospodáøské lesy smíšené','Lužní a mokøadní lesy','Ovocný sad, zahrada','Nesouvislá zástavba','Skály, sutì','Souvislá zástavba','Sportovní a rekreaèní plochy','Prùmyslové a obchodní jednotky','Dopravní sí','Mìstské zelené plochy, okrasná zahrada, park, høbitov']

            # List to store ids of features to remove
            ids_to_remove = []

            # Iterate over the features
            for feature in features:
                # Get the value in the 2nd column
                value = feature.attribute(second_column_index)
                
                # If the value does not match the name you want to keep
                if value not in names_to_keep:
                    # Add the feature id to the list of ids to remove
                    ids_to_remove.append(feature.id())

            # Remove the features
            provider.deleteFeatures(ids_to_remove)

            # Update the layer
            layer.updateFields()
       
        # Get the input vector layer
        vector_layer = self.parameterAsVectorLayer(parameters, 'inputv', context)

        extent = vector_layer.extent()
        xmin = extent.xMinimum()
        xmax = extent.xMaximum()
        ymin = extent.yMinimum()
        ymax = extent.yMaximum()
        extent = '{},{},{},{}'.format(xmin, xmax, ymin, ymax)
        print(extent)

        #correct the invalid geometries
        results['correctedlines'] = qtool.correctvector(parameters['kves'],paths['tempfiles'])

        #cut the fields with the vector layer extent ""def clipfields(woods, extent, path_dict):""
        results['clipedfields']= qtool.clipfields(results['correctedlines'],extent,paths['tempfiles'])
        print('clipedfields created')

        #dissolve the fields ""def dissolvefields(fields, path_dict):""
        results['dissolvedfields'] = qtool.dissolvefields(results['clipedfields'],paths['tempfiles'])
        print('dissolvedfields created')

        #buffer waterlines
        results['bufferedlines'] = qtool.buffering(parameters['inputv'],parameters['buffersize'],paths['tempfiles'])
        print('bufferedlines created')
        print(results['dissolvedfields'],results['bufferedlines'])

        #field difference
        results['fielddifference'] = qtool.fielddifference(results['bufferedlines'][1],results['dissolvedfields'],paths['tempfiles'])
        print('fielddifference created')

        # Assuming 'results['fielddifference']' is the path to your layer file
        layer = QgsVectorLayer(results['fielddifference'], "mokrad", "ogr")
    
        # Check if layer is valid
        if not layer.isValid():
            print("Layer failed to load!")
        else:
            # Add layer to QGIS
            QgsProject.instance().addMapLayer(layer)

        return results
