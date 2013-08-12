# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import xml.dom.minidom
import json
import os
import sys
import urllib2
from optparse import OptionParser
from textwrap import dedent
from os import path
from cs_entity_generator import write_entity_classes, get_actionable_entities



class cmdParameterProperty(object):
    def __init__(self):
        self.name = None
        self.required = False
        self.entity = ""
        self.desc = ""
        self.type = "planObject"
        self.subProperties = []


class cloudStackCmd(object):
    def __init__(self):
        self.name = ""
        self.desc = ""
        self.async = "false"
        self.entity = ""
        self.request = []
        self.response = []


class codeGenerator(object):
    """
    Apache CloudStack- marvin python classes can be generated from the json
    returned by API discovery or from the xml spec of commands generated by
    the ApiDocWriter. This class provides helper methods for these uses.
    """
    space = '    '
    newline = '\n'
    cmdsName = []

    def __init__(self, outputFolder):
        self.cmd = None
        self.code = ""
        self.required = []
        self.subclass = []
        self.outputFolder = outputFolder
        lic = """\
          # Licensed to the Apache Software Foundation (ASF) under one
          # or more contributor license agreements.  See the NOTICE file
          # distributed with this work for additional information
          # regarding copyright ownership.  The ASF licenses this file
          # to you under the Apache License, Version 2.0 (the
          # "License"); you may not use this file except in compliance
          # with the License.  You may obtain a copy of the License at
          #
          #   http://www.apache.org/licenses/LICENSE-2.0
          #
          # Unless required by applicable law or agreed to in writing,
          # software distributed under the License is distributed on an
          # "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
          # KIND, either express or implied.  See the License for the
          # specific language governing permissions and limitations
          # under the License.

          """
        self.license = dedent(lic)

    def addAttribute(self, attr, pro):
        value = pro.value
        if pro.required:
            self.required.append(attr)
        desc = pro.desc
        if desc is not None:
            self.code += self.space
            self.code += "''' " + pro.desc + " '''"
            self.code += self.newline

        self.code += self.space
        self.code += attr + " = " + str(value)
        self.code += self.newline

    def generateSubClass(self, name, properties):
        """Generate code for sub objects
        """
        subclass = 'class %s:\n'%name
        subclass += self.space + "def __init__(self):\n"
        for pro in properties:
            if pro.desc is not None:
                subclass += self.space + self.space + '""""%s"""\n' % pro.desc
            if len(pro.subProperties) > 0:
                subclass += self.space + self.space
                subclass += 'self.%s = []\n' % pro.name
                self.generateSubClass(pro.name, pro.subProperties)
            else:
                subclass += self.space + self.space
                subclass += 'self.%s = None\n' % pro.name

        self.subclass.append(subclass)

    def generateApiCmd(self, cmd):
        """Given an API cmd module generate the cloudstack cmd class in python
        """
        self.code = ""
        self.subclass = []
        self.cmd = cmd
        self.cmdsName.append(self.cmd.name)
        self.code = self.license
        self.code += self.newline
        self.code += '"""%s"""\n' % self.cmd.desc
        self.code += 'from baseCmd import *\n'
        self.code += 'from baseResponse import *\n'
        self.code += "class %sCmd (baseCmd):\n" % self.cmd.name
        self.code += self.space + "def __init__(self):\n"
        self.code += self.space + self.space
        self.code += 'self.isAsync = "%s"\n' % str(self.cmd.async).lower()
        self.code += self.space*2 + 'self.entity = "%s"\n' % self.cmd.entity

        for req in self.cmd.request:
            if req.desc is not None:
                self.code += self.space + self.space + '"""%s"""\n' % req.desc
            if req.required == "true":
                self.code += self.space + self.space + '"""Required"""\n'

            value = "None"
            if req.type == "list" or req.type == "map":
                value = "[]"

            self.code += self.space + self.space
            self.code += 'self.%s = %s\n' % (req.name, value)
            if req.required == "true":
                self.required.append(req.name)

        self.code += self.space + self.space + "self.required = ["
        for require in self.required:
            self.code += '"' + require + '",'
        self.code += "]\n"
        self.required = []

        """generate response code"""
        subItems = {}
        self.code += self.newline
        self.code += 'class %sResponse (baseResponse):\n' % self.cmd.name
        self.code += self.space + "def __init__(self):\n"
        if len(self.cmd.response) == 0:
            self.code += self.space + self.space + "pass"
        else:
            for res in self.cmd.response:
                if res.desc is not None:
                    self.code += self.space + self.space
                    self.code += '"""%s"""\n' % res.desc

                if len(res.subProperties) > 0:
                    self.code += self.space + self.space
                    self.code += 'self.%s = []\n' % res.name
                    self.generateSubClass(res.name, res.subProperties)
                else:
                    self.code += self.space + self.space
                    self.code += 'self.%s = None\n' % res.name
        self.code += self.newline

        for subclass in self.subclass:
            self.code += subclass + "\n"
        return self.code

    def write(self, out, modulename, code):
        """
        writes the generated code for `modulename` in the `out.cloudstackAPI` package
        @param out: absolute path where all api cmds are written to
        @param modulename: name of the module being written: eg: createNetwork
        @param code: Generated code
        @return: None
        """
        final_path = path.join(out, 'cloudstackAPI', modulename)
        module = final_path + '.py' #eg: out/cloudstackAPI/modulename.py
        with open(module, "w") as fp:
            fp.write(code)

    def finalize(self):
        """Generate an api call
        """
        header = '"""Marvin TestClient for CloudStack"""\n'
        imports = "import copy\n"
        initCmdsList = '__all__ = ['
        body = ''
        body += "class CloudStackAPIClient(object):\n"
        body += self.space + 'def __init__(self, connection):\n'
        body += self.space + self.space + 'self.connection = connection\n'
        body += self.space + self.space + 'self._id = None\n'
        body += self.newline

        body += self.space + 'def __copy__(self):\n'
        body += self.space + self.space
        body += 'return CloudStackAPIClient(copy.copy(self.connection))\n'
        body += self.newline

        # The `id` property will be used to link the test with the cloud
        # resource being created
        #            @property
        #            def id(self):
        #                return self._id
        #
        #            @id.setter
        #            def id(self, identifier):
        #                self._id = identifier

        body += self.space + '@property' + self.newline
        body += self.space + 'def id(self):' + self.newline
        body += self.space*2 + 'return self._id' + self.newline
        body += self.newline

        body += self.space + '@id.setter' + self.newline
        body += self.space + 'def id(self, identifier):' + self.newline
        body += self.space*2 + 'self._id = identifier' + self.newline
        body += self.newline

        for cmdName in self.cmdsName:
            body += self.space
            body += 'def %s(self, command, method="GET"):\n' % cmdName
            body += self.space + self.space
            body += 'response = %sResponse()\n' % cmdName
            body += self.space + self.space
            body += 'response = self.connection.marvinRequest(command,'
            body += ' response_type=response, method=method)\n'
            body += self.space + self.space + 'return response\n'
            body += self.newline

            imports += 'from %s import %sResponse\n' % (cmdName, cmdName)
            initCmdsList += '"%s",' % cmdName

        cloudstackApiClient = self.license + header + imports + body
        self.write(out=self.outputFolder, modulename='cloudstackAPIClient', code=cloudstackApiClient)

        '''generate __init__.py'''
        initCmdsList = self.license + initCmdsList + '"cloudstackAPIClient"]'
        self.write(out=self.outputFolder, modulename='__init__', code=initCmdsList)

        basecmd = self.license
        basecmd += '"""Base Command"""\n'
        basecmd += 'class baseCmd(object):\n'
        basecmd += self.space + 'pass\n'
        self.write(out=self.outputFolder, modulename='baseCmd', code=basecmd)

        baseResponse = self.license
        baseResponse += '"""Base Response"""\n'
        baseResponse += 'class baseResponse:\n'
        baseResponse += self.space + 'pass\n'
        self.write(out=self.outputFolder, modulename='baseResponse', code=baseResponse)

    def constructResponseFromXML(self, response):
        paramProperty = cmdParameterProperty()
        paramProperty.name = getText(response.getElementsByTagName('name'))
        paramProperty.desc = getText(response.
                                     getElementsByTagName('description'))
        if paramProperty.name.find('(*)') != -1:
            '''This is a list'''
            paramProperty.name = paramProperty.name.split('(*)')[0]
            argList = response.getElementsByTagName('arguments')[0].\
                getElementsByTagName('arg')
            for subresponse in argList:
                subProperty = self.constructResponseFromXML(subresponse)
                paramProperty.subProperties.append(subProperty)
        return paramProperty

    def loadCmdFromXML(self, dom):
        cmds = []
        for cmd in dom.getElementsByTagName("command"):
            csCmd = cloudStackCmd()
            csCmd.name = getText(cmd.getElementsByTagName('name'))
            assert csCmd.name
            if csCmd.name in ['login', 'logout']:
                continue

            csCmd.entity = getText(cmd.getElementsByTagName('entity'))
            assert csCmd.entity

            desc = getText(cmd.getElementsByTagName('description'))
            if desc:
                csCmd.desc = desc

            async = getText(cmd.getElementsByTagName('isAsync'))
            if async:
                csCmd.async = async

            argList = cmd.getElementsByTagName("request")[0].\
                getElementsByTagName("arg")
            for param in argList:
                paramProperty = cmdParameterProperty()

                paramProperty.name =\
                    getText(param.getElementsByTagName('name'))
                assert paramProperty.name

                required = param.getElementsByTagName('required')
                if required:
                    paramProperty.required = getText(required)

                requestDescription = param.getElementsByTagName('description')
                if requestDescription:
                    paramProperty.desc = getText(requestDescription)

                type = param.getElementsByTagName("type")
                if type:
                    paramProperty.type = getText(type)

                csCmd.request.append(paramProperty)

            responseEle = cmd.getElementsByTagName("response")[0]
            for response in responseEle.getElementsByTagName("arg"):
                if response.parentNode != responseEle:
                    continue

                paramProperty = self.constructResponseFromXML(response)
                csCmd.response.append(paramProperty)

            cmds.append(csCmd)
        return cmds

    def generateCodeFromXML(self, apiSpecFile):
        dom = xml.dom.minidom.parse(apiSpecFile)
        cmds = self.loadCmdFromXML(dom)
        for cmd in cmds:
            code = self.generateApiCmd(cmd)
            self.write(out=self.outputFolder, modulename=cmd.name, code=code)
        self.finalize()

    def constructResponseFromJSON(self, response):
        paramProperty = cmdParameterProperty()
        if 'name' in response:
            paramProperty.name = response['name']
        assert paramProperty.name, "%s has no property name" % response

        if 'description' in response:
            paramProperty.desc = response['description']
        if 'type' in response:
            if response['type'] in ['list', 'map', 'set']:
            #Here list becomes a subproperty
                if 'response' in response:
                    for innerResponse in response['response']:
                        subProperty =\
                            self.constructResponseFromJSON(innerResponse)
                        paramProperty.subProperties.append(subProperty)
            paramProperty.type = response['type']
        return paramProperty

    def loadCmdFromJSON(self, apiStream):
        if apiStream is None:
            raise Exception("No APIs found through discovery")

        jsonOut = apiStream.readlines()
        assert len(jsonOut) > 0
        apiDict = json.loads(jsonOut[0])
        if not 'listapisresponse' in apiDict:
            raise Exception("API discovery plugin response failed")
        if not 'count' in apiDict['listapisresponse']:
            raise Exception("Malformed api response")

        apilist = apiDict['listapisresponse']['api']
        cmds = []
        for cmd in apilist:
            csCmd = cloudStackCmd()
            if 'name' in cmd:
                csCmd.name = cmd['name']
            assert csCmd.name
            if csCmd.name in ['login', 'logout']:
                continue

            if cmd.has_key('entity'):
                csCmd.entity = cmd['entity']
            else:
                print csCmd.name + " has no entity"

            if 'description' in cmd:
                csCmd.desc = cmd['description']

            if 'isasync' in cmd:
                csCmd.async = cmd['isasync']

            for param in cmd['params']:
                paramProperty = cmdParameterProperty()

                if 'name' in param:
                    paramProperty.name = param['name']
                assert paramProperty.name

                if 'required' in param:
                    paramProperty.required = param['required']

                if 'description' in param:
                    paramProperty.desc = param['description']

                if 'type' in param:
                    paramProperty.type = param['type']

                csCmd.request.append(paramProperty)

            for response in cmd['response']:
            #FIXME: ExtractImage related APIs return empty dicts in response
                if len(response) > 0:
                    paramProperty = self.constructResponseFromJSON(response)
                    csCmd.response.append(paramProperty)

            cmds.append(csCmd)
        return cmds

    def generateCodeFromJSON(self, endpointUrl):
        """
        Api Discovery plugin returns the supported APIs of a CloudStack
        endpoint.
        @return: The classes in cloudstackAPI/ formed from api discovery json
        """
        if endpointUrl.find('response=json') >= 0:
                apiStream = urllib2.urlopen(endpointUrl)
                cmds = self.loadCmdFromJSON(apiStream)
                for cmd in cmds:
                    code = self.generateApiCmd(cmd)
                    self.write(out=self.outputFolder, modulename=cmd.name, code=code)
                self.finalize()


def getText(elements):
    return elements[0].childNodes[0].nodeValue.strip()

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-o", "--output", dest="output",
                      help="The path to the generated code entities, default\
 is .")
    parser.add_option("-s", "--specfile", dest="spec",
                      help="The path and name of the api spec xml file,\
 default is /etc/cloud/cli/commands.xml")
    parser.add_option("-e", "--endpoint", dest="endpoint",
                      help="The endpoint mgmt server (with open 8096) where\
 apis are discovered, default is localhost")
    parser.add_option("-y", "--entity", dest="entity",
                      help="Generate entity based classes")

    (options, args) = parser.parse_args()

    folder = "."
    if options.output is not None:
        folder = options.output
    apiModule = folder + "/cloudstackAPI"
    if not os.path.exists(apiModule):
        try:
            os.mkdir(apiModule)
        except:
            print "Failed to create folder %s, due to %s" % (apiModule,
                                                             sys.exc_info())
            print parser.print_help()
            exit(2)

    apiSpecFile = "/etc/cloud/cli/commands.xml"
    if options.spec is not None:
        apiSpecFile = options.spec
        if not os.path.exists(apiSpecFile):
            print "the spec file %s does not exists" % apiSpecFile
            print parser.print_help()
            exit(1)

    cg = codeGenerator(folder)
    if options.spec is not None:
        cg.generateCodeFromXML(apiSpecFile)
    elif options.endpoint is not None:
        endpointUrl = 'http://%s:8096/client/api?command=listApis&\
response=json' % options.endpoint
        cg.generateCodeFromJSON(endpointUrl)

    if options.entity:
        entities = get_actionable_entities(path=apiModule)
        write_entity_classes(entities, "base2")
