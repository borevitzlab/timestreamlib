#!/usr/bin/python
# coding=utf-8
# Copyright (C) 2014
# Author(s): Joel Granados <joel.granados@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os.path
import yaml


class PCFGException(Exception):

    def __str__(self):
        return "Pipeline Configuration Error: %s" % self.message


class PCFGExInvalidSubsection(PCFGException):

    def __init__(self, name):
        self.message = "Invalid subsection %s" % name


class PCFGExInvalidFile(PCFGException):

    def __init__(self, name):
        self.message = "Invalid Configuration File %s" % name


class PCFGExInvalidType(PCFGException):

    def __init__(self, E, T):
        self.message = "Expected a %s got a %s instead" % (E, T)


class PCFGSection(object):

    def __init__(self, name):
        """ Generic configuration subsection

        Args:
          name (str): Name of self section. Used for __str__ only
        """
        self.__dict__["__subsections"] = {}

    def __getattr__(self, key):
        if key not in self.__dict__["__subsections"]:
            raise PCFGExInvalidSubsection(key)

        return self.__dict__["__subsections"][key]

    def __setattr__(self, key, value):
        self.__dict__["__subsections"][key] = value

    def addSubSec(self, key, value):
        self.__dict__["__subsections"][key] = value

    def getVal(self, index):
        """ Will return a value or a subsection

        Its different from __getattr__ is that you can pass it a string.

        Args:
          index (str): Of the form "pipeline.undistort.arg1"
          index (list): Of the form ["pipeline", "undistort", "arg1"]
        """
        if isinstance(index, str):
            index = index.split(".")
        if not isinstance(index, list):
            raise PCFGExInvalidType("list or str", type(index))
        if len(index) < 1:
            raise PCFGExInvalidType("list of len>1", "list of len<1")
        if index[0] not in self.__dict__["__subsections"]:
            raise PCFGExInvalidSubsection(index[0])

        retVal = None
        # We look for the value in the nested section
        if len(index) > 1:
            if not isinstance(self.__dict__["__subsections"][index[0]],
                              PCFGSection):
                raise PCFGExInvalidSubsection(index[0])
            else:
                retVal = self.__dict__["__subsections"][index[0]]. \
                    getVal(index[1:])

        elif len(index) == 1:
            retVal = self.__dict__["__subsections"][index[0]]

        else:
            raise PCFGExInvalidSubsection(index[0])

        return retVal

    def setVal(self, index, value):
        """ Will set a value. Not a subsection.

        It differs from __setattr__ in that in deals only in values.
        This function is called recursively

        Args:
          index (str): Of the form "pipeline.undistort.arg1"
          index (list): Of the form ["pipeline", "undistort", "arg1"]
          value (non PCFGSection): Any value that is not PCFGSection
        """
        if isinstance(index, str):
            index = index.split(".")
        if not isinstance(index, list):
            raise PCFGExInvalidType("list or str", type(index))
        if len(index) < 1:
            raise PCFGExInvalidType("list of len>1", "list of len<1")

        # set the value in the nested section
        if len(index) > 1:
            # If doesn't exist, create it!
            if index[0] not in self.__dict__["__subsections"]:
                tmpSec = PCFGSection(index[0])
                self.__dict__["__subsections"][index[0]] = tmpSec

            # if exists but its not a subsection
            if not isinstance(self.__dict__["__subsections"][index[0]],
                              PCFGSection):
                raise PCFGExInvalidSubsection(index[0])

            self.__dict__["__subsections"][index[0]].setVal(index[1:], value)

        else:
            # If doesn't exist, create it!
            if index[0] not in self.__dict__["__subsections"]:
                self.__dict__["__subsections"][index[0]] = None

            if isinstance(self.__dict__["__subsections"][index[0]],
                          PCFGSection):
                raise PCFGExInvalidType(
                    "non PCFGSection",
                    type(self.__dict__["__subsections"][index[0]]))
            else:
                self.__dict__["__subsections"][index[0]] = value

    def listIndexes(self, withVals=False, endline=""):
        """Return the total tree of suboptions"""
        retStr = []
        for key in self.__dict__["__subsections"].keys():
            tmpstr = None
            if isinstance(self.__dict__["__subsections"][key], PCFGSection):
                tmpstr = self.__dict__["__subsections"][key].\
                    listIndexes(withVals, endline)
                for i in range(len(tmpstr)):
                    tmpstr[i] = key + "." + tmpstr[i]
                retStr.extend(tmpstr)

            else:  # Config value
                tmpstr = ""
                if withVals:
                    tmpstr = "=" + str(self.__dict__["__subsections"][key])
                retStr.append(str(key) + tmpstr + endline)

        return retStr

    def iter_by_index(self):
        for index in self.listIndexes():
            yield(index)

    def iter_as_list(self):
        """Special iterator for lists that got converted to dicts.

        All PCFGSection get changed to dictionaries
        """
        # When encountering lists in configuration files we translated 0 to _0 in
        # order to allow point "." naming (python does not allow subsection.0). This
        # means that the list is temporarily lost. This iterator will return the
        # list values in order with their index. Only works for subsections that
        # have keys of the type _{number}.

        if False in [x.startswith("_")
                     for x in self.__dict__["__subsections"].keys()]:
            raise PCFGExInvalidType("_ prefix", "non _ prefix")

        # transform string keys into sorted nubmers
        numKeys = sorted([int(x.strip("_"))
                          for x in self.__dict__["__subsections"].keys()])

        for numKey in numKeys:
            strKey = "_" + str(numKey)
            valKey = None

            if isinstance(self.__dict__["__subsections"][strKey], PCFGSection):
                valKey = self.__dict__["__subsections"][strKey].asDict()
            else:
                valKey = self.__dict__["__subsections"][strKey]
            yield(numKey, valKey)

    def listSubSecNames(self):
        """Return a list of subsection names"""
        return self.__dict__["__subsections"].keys()

    def asDict(self):
        """Return dictionary representation of the tree"""
        retDict = {}
        for key in self.__dict__["__subsections"].keys():
            retDict[key] = None
            if isinstance(self.__dict__["__subsections"][key], PCFGSection):
                retDict[key] = self.__dict__["__subsections"][key].asDict()
            else:
                retDict[key] = self.__dict__["__subsections"][key]

        return retDict

    def hasSubSecName(self, name):
        return name in self.__dict__["__subsections"]

    @property
    def size(self):
        return len(self.__dict__["__subsections"])


class PCFGConfig(PCFGSection):

    def __init__(self, configFile, depth):
        """PCFGConfig houses all config options

        Args:
          _configFile: Full path of the configuration file
          _depth: PCFGConfig depends on nested dictionaries. "depth" defines the
                 recursion depth to where options will be searched.
                 (e.g config.opt1.opt2=3 has depth 2).
        """
        super(PCFGConfig, self).__init__("--")
        if not os.path.exists(configFile) or not os.path.isfile(configFile):
            raise PCFGExInvalidFile(configFile)
        self._configFile = configFile
        self._depth = depth

        # To load from another config format create a loadFrom function
        for func in [self.loadFromYaml]:
            try:
                confDict = func()
            except:
                continue
            break

        # Equal __subsections to allow instance.element.element....
        tmpSubSec = PCFGConfig.createSection(confDict, self._depth, "-")
        self.__dict__["__subsections"] = tmpSubSec.__dict__["__subsections"]

    def loadFromYaml(self):
        f = file(self._configFile)
        yDict = yaml.load(f)
        f.close()

        return yDict

    def __str__(self):
        return "".join(self.listIndexes(withVals=True, endline="\n"))

    @classmethod
    def createSection(cls, confElems, depth, name):
        """ Initialize configuration sections from dictionary.

        Stop recursion when value different than dict or list
        """
        retVal = None
        if isinstance(confElems, dict):
            retVal = PCFGSection(name)
            if depth > 0:
                for key in confElems.keys():
                    retVal.addSubSec(key,
                                     cls.createSection(confElems[key],
                                                       depth - 1, key))
            else:
                for key in confElems.keys():
                    retVal.addSubSec(key, confElems[key])

        elif isinstance(confElems, list):
            retVal = PCFGSection(name)
            if depth > 0:
                for i in range(len(confElems)):
                    retVal.addSubSec("_%d" % i,
                                     cls.createSection(confElems[i],
                                                       depth - 1, "_%d" % i))
            else:
                for i in range(len(confElems)):
                    retVal.addSubSec("_%d" % i, confElems[i])

        else:
            # We stop. Even depth == 0 has not been reached.
            retVal = confElems

        return retVal

    @classmethod
    def merge(cls, A, B):
        """ Merge the contents of A onto B.

        All what is in A will be create or replaced in B

        Args:
          A,B (PCFGConfig): Configuration instances
        """

        for aindex in A.iter_by_index():
            B.setVal(aindex, A.getVal(aindex))
