# -*- coding: utf-8 -*-

"""
***************************************************************************
    whiteboxDescriptions.py
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


import re
import os
import json
import argparse
import tempfile
import subprocess

nameRegex = re.compile('[A-Z][a-z]*')


def whiteboxTools():
    tools = None

    command = ['whitebox_tools --listtools']
    with subprocess.Popen(command,
                          shell=True,
                          stdout=subprocess.PIPE,
                          stdin=subprocess.DEVNULL,
                          stderr=subprocess.STDOUT,
                          universal_newlines=True) as proc:
        try:
            tools = dict()
            for line in proc.stdout:
                if 'Available Tools' in line:
                    continue
                elif line == '\n':
                    continue
                t = line.strip().split(':')
                toolName = t[0].strip()
                toolHelp = t[1].strip()
                tools[toolName] = toolHelp[:-1]
        except Exception as e:
            print("Can not get list of the available tools:\n{}".format(str(e)))
            return None

        return tools


def createDescriptions(descriptionPath):
    tools = whiteboxTools()

    for tool, shortHelp in tools.items():
        print("\nPROCESS TOOL", tool)
        params = ""
        command = ['whitebox_tools --toolparameters="{}"'.format(tool)]
        with subprocess.Popen(command,
                              shell=True,
                              stdout=subprocess.PIPE,
                              stdin=subprocess.DEVNULL,
                              stderr=subprocess.STDOUT,
                              universal_newlines=True) as proc:
            try:
                for line in proc.stdout:
                    params += line
            except Exception as e:
                print("Can not get parameters for tool {}:\n{}".format(tool, str(e)))
                continue

        j = json.loads(params)

        # collect inputs
        params = []
        for p in j['parameters']:
            parameterType = p['parameter_type']
            if 'ExistingFileOrFloat' in parameterType or 'ExistingFile' in parameterType:
                param = _fileParameter(p)
                if param:
                    params.append(param)
                else:
                    print(' - failed to process parameter:\n{}'.format(p))
            elif 'FileList' in parameterType:
                param = _multifileParameter(p)
                if param:
                    params.append(param)
                else:
                    print(' - failed to process parameter:\n{}'.format(p))
            elif 'OptionList' in parameterType:
                params.append(_enumParameter(p))
            elif 'Boolean' in parameterType:
                params.append(_booleanParameter(p))
            elif 'Float' in parameterType or 'Integer' in parameterType:
                params.append(_numberParameter(p))
            elif 'String' in parameterType:
                params.append(_stringParameter(p))
            else:
                param = _otherParameter(p)
                if param is not None:
                    print(param)

        # collect outputs
        for p in j['parameters']:
            parameterType = p['parameter_type']
            if 'NewFile' in parameterType:
                param = _fileOutput(p)
                if param:
                    params.append(param)
                else:
                    print(' - failed to process parameter:\n{}'.format(p))

        with open(os.path.join(descriptionPath, '{}.txt'.format(tool)), 'w') as f:
            f.write('{}\n'.format(tool))
            f.write('{}\n'.format(' '.join(nameRegex.findall(tool))))
            f.write('{}\n'.format(shortHelp))
            f.write('{}\n'.format('\n'.join(params)))


def _fileParameter(param):
    name = param['flags'][0].lstrip('-') if len(param['flags']) == 1 else param['flags'][1].lstrip('-')
    description = param['description'][:-1]
    optional = True if param['optional'] == 'true' else False
    parameterType = param['parameter_type']

    if 'ExistingFileOrFloat' in parameterType:
        dataType = param['parameter_type']['ExistingFileOrFloat']
    elif 'ExistingFile' in parameterType:
        dataType = param['parameter_type']['ExistingFile']
    else:
        return None

    if dataType == 'Raster':
        return 'QgsProcessingParameterRasterLayer|{}|{}|None|{}'.format(name, description, optional)
    if dataType == 'Text':
        return 'QgsProcessingParameterFile|{}|{}|QgsProcessingParameterFile.File|txt|None|{}'.format(name, description, optional)
    if dataType == 'HTML':
        return 'QgsProcessingParameterFile|{}|{}|QgsProcessingParameterFile.File|html|None|{}'.format(name, description, optional)
    if dataType == 'Lidar':
        return 'QgsProcessingParameterFile|{}|{}|QgsProcessingParameterFile.File|las|None|{}'.format(name, description, optional)
    else:
        return None


def _multifileParameter(param):
    name = param['flags'][0].lstrip('-') if len(param['flags']) == 1 else param['flags'][1].lstrip('-')
    description = param['description'][:-1]
    optional = True if param['optional'] == 'true' else False
    dataType = param['parameter_type']['FileList']

    if dataType == 'Raster':
        return 'QgsProcessingParameterMultipleLayers|{}|{}|3|None|False'.format(name, description, optional)
    else:
        return None


def _enumParameter(param):
    name = param['flags'][0].lstrip('-') if len(param['flags']) == 1 else param['flags'][1].lstrip('-')
    description = param['description'][:-1]
    optional = True if param['optional'] == 'true' else False
    options = [v.strip('"') for v in param['parameter_type']['OptionList']]
    defaultValue = options.index(param['default_value'])
    return 'QgsProcessingParameterEnum|{}|{}|{}|False|{}|{}'.format(name, description, ';'.join(options), defaultValue, optional)


def _booleanParameter(param):
    name = param['flags'][0].lstrip('-') if len(param['flags']) == 1 else param['flags'][1].lstrip('-')
    description = param['description']
    optional = True if param['optional'] == 'true' else False
    defaultValue = True if param['default_value'] == 'true' else False
    return 'QgsProcessingParameterBoolean|{}|{}|{}|{}'.format(name, description, defaultValue, optional)


def _numberParameter(param):
    name = param['flags'][0].lstrip('-') if len(param['flags']) == 1 else param['flags'][1].lstrip('-')
    description = param['description']
    optional = True if param['optional'] == 'true' else False
    dataType = param['parameter_type']
    defaultValue = param['default_value']

    if dataType == 'Integer':
        return 'QgsProcessingParameterNumber|{}|{}|QgsProcessingParameterNumber.Integer|{}|{}|None|None'.format(name, description, defaultValue, optional)
    else:
        return 'QgsProcessingParameterNumber|{}|{}|QgsProcessingParameterNumber.Double|{}|{}|None|None'.format(name, description, defaultValue, optional)


def _stringParameter(param):
    name = param['flags'][0].lstrip('-') if len(param['flags']) == 1 else param['flags'][1].lstrip('-')
    description = param['description'][:-1]
    optional = True if param['optional'] == 'true' else False
    defaultValue = param['default_value']
    return 'QgsProcessingParameterString|{}|{}|{}|False|{}'.format(name, description, defaultValue, optional)


def _otherParameter(param):
    name = param['flags'][0].lstrip('-') if len(param['flags']) == 1 else param['flags'][1].lstrip('-')
    description = param['description'][:-1]
    optional = True if param['optional'] == 'true' else False
    parameterType = param['parameter_type']
    if 'NewFile' in parameterType:
        return None
    else:
        return ' - unsupported parameter:\n{}'.format(param)


def _fileOutput(param):
    name = param['flags'][0].lstrip('-') if len(param['flags']) == 1 else param['flags'][1].lstrip('-')
    description = param['description'][:-1]
    optional = True if param['optional'] == 'true' else False
    parameterType = param['parameter_type']

    if 'NewFile' in parameterType:
        dataType = param['parameter_type']['NewFile']
    else:
        return None

    if dataType == 'Raster':
        return 'QgsProcessingParameterRasterDestination|{}|{}|None|{}'.format(name, description, optional)
    elif dataType == 'Html':
        return 'QgsProcessingParameterFileDestination|{}|{}|HTML files (*.html *.HTML)|None|{}'.format(name, description, optional)
    elif dataType == 'Lidar':
        return 'QgsProcessingParameterFileDestination|{}|{}|LIDAR files (*.las *.LAS)|None|{}'.format(name, description, optional)
    else:
        return ' - unsupported parameter:\n{}'.format(param)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate Whitebox Tools descriptions for Processing.')
    parser.add_argument('directory', metavar='DIRECTORY', nargs='?', default=tempfile.gettempdir(), help='output directory')
    args = parser.parse_args()

    createDescriptions(args.directory)
