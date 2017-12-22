# -*- coding: utf-8 -*-

"""
***************************************************************************
    whiteboxAlgorithm.py
    ---------------------
    Date                 : December 2017
    Copyright            : (C) 2017 by Alexander Bruy
    Email                : alexander dot bruy at gmail dot com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

__author__ = 'Alexander Bruy'
__date__ = 'December 2017'
__copyright__ = '(C) 2017, Alexander Bruy'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os

from qgis.PyQt.QtGui import QIcon
from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterFile,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterString,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterMultipleLayers,
                       QgsProcessingParameterRasterDestination,
                       QgsProcessingParameterFileDestination,
                       QgsProcessingOutputHtml,
                       QgsProcessingOutputFile
                      )
from processing.core.parameters import getParameterFromString
from processing.tools.system import isWindows

from processing_whitebox import whiteboxUtils

pluginPath = os.path.dirname(__file__)


class WhiteboxAlgorithm(QgsProcessingAlgorithm):

    def __init__(self, descriptionFile):
        super().__init__()

        self.descriptionFile = descriptionFile
        self._name = ''
        self._displayName = ''
        self._group = 'Whitebox Tools'
        self._groupId = 'whiteboxtools'
        self._shortHelp = ''

        self.params = []

        self.defineCharacteristicsFromFile()

    def createInstance(self):
        return self.__class__(self.descriptionFile)

    def name(self):
        return self._name

    def displayName(self):
        return self._displayName

    def group(self):
        return self._group

    def groupId(self):
        return self._groupId

    def shortHelpString(self):
        return self._shortHelp

    def icon(self):
        return QIcon(os.path.join(pluginPath, 'icons', 'whiteboxtools.png'))

    def tr(self, text):
        return QCoreApplication.translate("WhiteboxAlgorithm", text)

    def initAlgorithm(self, config=None):
        for p in self.params:
            self.addParameter(p, True)

            # file destinations are not automatically added as outputs
            if isinstance(p, QgsProcessingParameterFileDestination):
                if p.defaultFileExtension().lower() == 'html':
                    self.addOutput(QgsProcessingOutputHtml(p.name(), p.description()))
                elif p.defaultFileExtension().lower() == 'las':
                    self.addOutput(QgsProcessingOutputFile(p.name(), p.description()))

    def defineCharacteristicsFromFile(self):
        with open(self.descriptionFile) as lines:
            line = lines.readline().strip('\n').strip()
            self._name = line

            line = lines.readline().strip('\n').strip()
            self._displayName = line

            line = lines.readline().strip('\n').strip()
            self._shortHelp = line

            line = lines.readline().strip('\n').strip()
            while line != '':
                self.params.append(getParameterFromString(line))
                line = lines.readline().strip('\n').strip()

    def processAlgorithm(self, parameters, context, feedback):
        wb = whiteboxUtils.whiteboxToolsExecutable()
        if wb == '':
            wb = 'whitebox_tools'

        arguments = [wb]
        arguments.append('--run={}'.format(self.name()))

        for param in self.parameterDefinitions():
            if param.isDestination():
                continue

            if isinstance(param, QgsProcessingParameterRasterLayer):
                layer = self.parameterAsRasterLayer(parameters, param.name(), context)
                arguments.append('--{}="{}"'.format(param.name(), layer.source()))
            elif isinstance(param, QgsProcessingParameterMultipleLayers):
                layers = self.parameterAsLayerList(parameters, param.name(), context)
                if layers is None or len(layers) == 0:
                    continue
                if param.layerType() == QgsProcessing.TypeRaster:
                    files = [layer.source() for layer in layers]
                arguments.append('--{}="{}"'.format(param.name(), ','.join(files)))
            elif isinstance(param, QgsProcessingParameterBoolean):
                arguments.append('--{}="{}"'.format(param.name(), self.parameterAsBool(parameters, param.name(), context)))
            elif isinstance(param, QgsProcessingParameterNumber):
                arguments.append('--{}={}'.format(param.name(), self.parameterAsDouble(parameters, param.name(), context)))
            elif isinstance(param, QgsProcessingParameterEnum):
                arguments.append('--{}="{}"'.format(param.name(), self.parameterAsEnum(parameters, param.name(), context)))
            elif isinstance(param, (QgsProcessingParameterString, QgsProcessingParameterFile)):
                arguments.append('--{}="{}"'.format(param.name(), self.parameterAsFile(parameters, param.name(), context)))
            elif isinstance(param, (QgsProcessingParameterString)):
                arguments.append('--{}="{}"'.format(param.name(), self.parameterAsString(parameters, param.name(), context)))
            else:
                arguments.append('--{}="{}"'.format(param.name(), self.parameterAsInt(parameters, param.name(), context)))

        for out in self.destinationParameterDefinitions():
            if isinstance(out, QgsProcessingParameterRasterDestination):
                arguments.append('--{}="{}"'.format(out.name(), self.parameterAsOutputLayer(parameters, out.name(), context)))
            elif isinstance(out, QgsProcessingParameterFileDestination):
                arguments.append('--{}="{}"'.format(out.name(), self.parameterAsFileOutput(parameters, out.name(), context)))

        arguments.append('-v')

        whiteboxUtils.execute(arguments, feedback)

        results = {}
        for output in self.outputDefinitions():
            outputName = output.name()
            if outputName in parameters:
                results[outputName] = parameters[outputName]

        return results
