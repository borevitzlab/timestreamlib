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


class PCFGExLockedSection(PCFGException):

    def __init__(self, name):
        self.message = "Subsection %s locked" % name


class PCFGSection(object):

    def __init__(self, name):
        """ Generic configuration subsection

        Args:
          name (str): Name of self section. Used for __str__ only
        """
        self.__dict__["__subsections"] = {}
        self.__dict__["_name"] = name
        self.__dict__["_locked"] = False

    def __getattr__(self, key):
        if key not in self.__dict__["__subsections"]:
            raise PCFGExInvalidSubsection(key)

        return self.__dict__["__subsections"][key]

    def __setattr__(self, key, value):
        if self.__dict__["_locked"]:
            raise PCFGExLockedSection(self.__dict__["_name"])
        self.__dict__["__subsections"][key] = value

    def lock(self):
        self.__dict__["_locked"] = True
        for _, sec in self.__dict__["__subsections"].iteritems():
            if isinstance(sec, PCFGSection):
                sec.lock()

    def unlock(self):
        self.__dict__["_locked"] = False
        for _, sec in self.__dict__["__subsections"].iteritems():
            if isinstance(sec, PCFGSection):
                sec.unlock()

    def locked(self):
        return self.__dict__["_locked"]

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
        """ Will set a value.

        It differs from __setattr__ in that in deals only in values.
        This function is called recursively

        Args:
          index (str): Of the form "pipeline.undistort.arg1"
          index (list): Of the form ["pipeline", "undistort", "arg1"]
          value (object): Any value that is not PCFGSection
        """
        if self.__dict__["_locked"]:
            raise PCFGExLockedSection(self.__dict__["_name"])
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

    def listTree(self, withVals=False, endline=""):
        """Return the total tree of suboptions"""
        retStr = []
        for key in self.__dict__["__subsections"].keys():
            tmpstr = None
            if isinstance(self.__dict__["__subsections"][key], PCFGSection):
                tmpstr = self.__dict__["__subsections"][key].\
                    listTree(withVals, endline)
                for i in range(len(tmpstr)):
                    tmpstr[i] = key + "." + tmpstr[i]
                retStr.extend(tmpstr)

            else:  # Config value
                tmpstr = ""
                if withVals:
                    tmpstr = "=" + str(self.__dict__["__subsections"][key])
                retStr.append(str(key) + tmpstr + endline)

        return retStr

    def itertree(self):
        """Iterate through all the tree"""
        for index in self.listTree():
            yield(index)

    def itersections(self):
        """Iterate through this sections __subsection"""
        for key, val in self.__dict__["__subsections"].iteritems():
            yield(key, val)

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


class PCFGListSection(PCFGSection):

    def __init__(self, name):
        """ Section specifically for lists.

        When encountering lists in configuration files we translated 0 to _0 in
        order to allow point "." naming (python does not allow subsection.0).
        This class will handle the list values in order with their index.
        """
        super(PCFGListSection, self).__init__(name)

    def __getattr__(self, offset):
        if not offset.startswith("_"):
            offset = "_%s" % offset
        return super(PCFGListSection, self).__getattr__(offset)

    def __setattr__(self, offset, value):
        if not offset.startswith("_"):
            offset = "_%s" % offset
        super(PCFGListSection, self).__setattr__(offset, value)

    def getVal(self, index):
        if isinstance(index, str):
            index = index.split(".")
        if isinstance(index, int):
            index = ["_%s" % index]
        if not isinstance(index, list):
            raise PCFGExInvalidType("list or str", type(index))
        if not index[0].startswith("_"):
            index[0] = "_%s" % index[0]
        return super(PCFGListSection, self).getVal(index)

    def setVal(self, index, value):
        if isinstance(index, str):
            index = index.split(".")
        if isinstance(index, int):
            index = ["_%s" % index]
        if not isinstance(index, list):
            raise PCFGExInvalidType("list or str", type(index))
        if not index[0].startswith("_"):
            index[0] = "_%s" % index[0]
        super(PCFGListSection, self).setVal(index, value)

    def itersections(self):
        """Special iterator for lists that got converted to dicts.

        All PCFGSection get changed to dictionaries
        Only works for subsections that have keys of the type _{number}.
        """
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

    def hasSubSecName(self, name):
        if not isinstance(name, str):
            name = "_%d" % name
        return name in self.__dict__["__subsections"]


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
        return "".join(self.listTree(withVals=True, endline="\n"))

    @classmethod
    def createSection(cls, confElems, depth, name):
        """ Initialize configuration sections from dictionary.

        Stop recursion when value different than dict or list
        """
        retVal = None
        if isinstance(confElems, dict):
            retVal = PCFGSection(name)
            inds = confElems.keys()
        elif isinstance(confElems, list):
            retVal = PCFGListSection(name)
            inds = range(len(confElems))
        elif confElems is None:
            return PCFGSection(name)
        else:
            return confElems

        if depth > 0:
            for i in inds:
                retVal.setVal(i, cls.createSection(confElems[i], depth - 1, i))
        else:
            for i in inds:
                retVal.setVal(i, confElems[i])

        return retVal

    @classmethod
    def merge(cls, A, B):
        """ A onto B. Elements of A will be create or replaced in B

        Args:
          A,B (PCFGConfig): Configuration instances
        """

        for aindex in A.itertree():
            B.setVal(aindex, A.getVal(aindex))
