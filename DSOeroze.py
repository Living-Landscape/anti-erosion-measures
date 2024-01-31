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
            QgsProcessingParameterNumber(
                'watershedbasins','Increase number to generate more significant streams', 
                type=QgsProcessingParameterNumber.Integer,  # Type of the number 
                minValue=5,  # Minimum allowed value
                maxValue=1000000,  # Maximum allowed value
                defaultValue=30000  # Default value (optional)
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                'visualize','1 = plot, 0 = no plot', 
                type=QgsProcessingParameterNumber.Integer,  # Type of the number 
                minValue=0,  # Minimum allowed value
                maxValue=1,  # Maximum allowed value
                defaultValue=1 # Default value (optional)
            )
        )

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                'inputv','Polygon to cut fields', 
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


        # Get the input raster layer
        raster_layer = self.parameterAsRasterLayer(parameters, 'inputr', context)

        extent = raster_layer.extent()
        xmin = extent.xMinimum()
        xmax = extent.xMaximum()
        ymin = extent.yMinimum()
        ymax = extent.yMaximum()
        extent = '{},{},{},{}'.format(xmin, xmax, ymin, ymax)
        print(extent)

        #create depresionless DEM
        results['depresionless_dem'] = qtool.filterDEM(parameters['inputr'],paths['tempfiles'])
        print('depresionless_dem created')

        #calculate the watershed
        results['watershed'] = qtool.watershed(results['depresionless_dem'],paths['tempfiles'],parameters['watershedbasins']) 
        print('watershed created')

        #cut the fields with the raster layer extent ""def clipfields(fields, raster, path_dict):""
        results['clipedfields']= qtool.clipfields(parameters['inputv'],extent,paths['tempfiles'])
        print('clipedfields created')

        #dissolve the fields ""def dissolvefields(fields, path_dict):""
        results['dissolvedfields'] = qtool.dissolvefields(results['clipedfields'],paths['tempfiles'])
        print('dissolvedfields created')

        #cut the watershed with the field polygon ""def cutraster(raster,polygon,path_dict):""
        results['cuttedwatershed'] = qtool.cutraster(results['watershed'],results['dissolvedfields'],paths['tempfiles'])
        print('cuttedwatershed created')

        #polygonize the raster 
        results['polygonizedwatershed'] = qtool.rastertopolygon(results['cuttedwatershed'],paths['tempfiles'])
        print('polygonizedwatershed created')

        #polygon to line   
        results['linedpolygon'] = qtool.polygontoline(results['polygonizedwatershed'],paths['tempfiles'])
        print('linedpolygon created')

        #buffer the DSO 
        results['bufferedlines'] = qtool.buffering(results['linedpolygon'],paths['tempfiles'])
        print('bufferedlines created')
        


        # Assuming 'results['bufferedlines']' is the path to your layer file
        layer = QgsVectorLayer(results['bufferedlines'][1], "grass_DSO", "ogr") # [1] is the second element in OUTPUT dictionary
        
        
        # Check if layer is valid
        if not layer.isValid():
            print("Layer failed to load!")
        else:
            # Add layer to QGIS
            QgsProject.instance().addMapLayer(layer)



            






        return results
    