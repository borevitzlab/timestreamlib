# Copyright 2006-2014 Tim Brown/TimeScience LLC
# Copyright 2013-2014 Kevin Murray/Bioinfinio
# Copyright 2014- The Australian National Univesity
# Copyright 2014- Joel Granados
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
.. module:: timestream.manipulate.configuration
    :platform: Unix, Windows
    :synopsis: Pipeline management configuration

.. moduleauthor:: Joel Granados
"""

import os.path
import datetime
from textwrap import TextWrapper
import yaml


class PCFGException(Exception):

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return "Pipeline Configuration Error: %s" % self.message


class PCFGExOnLoadConfig(PCFGException):

    def __init__(self, path):
        self.message = "Error loading %s configuration" % path


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


class PCFGExMissingRequiredArgument(PCFGException):

    def __init__(self, name):
        self.message = "Subsection %s is missing" % name


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

    def getVal(self, index, pop=False):
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
            if pop:
                retVal = self.__dict__["__subsections"].pop(index[0])
            else:
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

    argNames = [
        {"arg": "pipeline", "type": PCFGListSection,
         "def": [], "req": True,
         "doc": "A list of pipeline components that take action on a "
            "Time Stream",
         "ex": "pipeline:- name: undistort- name: colorcarddetect"},
        {"arg": "outstreams", "type": PCFGListSection,
         "def": [], "req": False,
         "doc": "A list of output stream names that get translated into "
            "output stream directories. These names are to be used "
            "with output components such as the image writer.",
         "ex": "outstreams:  - { name: cor }  - { name: seg }"},
        {"arg": "general", "type": PCFGSection, "def": [], "req": True,
         "doc": "List of general settings that will define the behavior "
            "of the pipeline. Some of these include date range, "
            "time range and time interval.",
         "ex": "general:  timeInterval: 900  visualise: False"},
        {"arg": "general.startDate", "type": PCFGSection,
         "def": None, "req": False,
         "doc": "The starting date of the Time Stream. All prior dates "
            "will be ignored. It contains six elements: year, "
            "month, day, hour, minute, second.",
         "ex":  "startDate: { year: 2014, month: 06, day: 25, "
            "hour: 9, minute: 0, second: 0 }"},
        {"arg": "general.endDate", "type": PCFGSection,
         "def": None, "req": False,
         "doc": "The ending date of the Time Stream. Ignore all posterior "
            "dates. It contains six elements: year, month, day, "
            "hour, minute, second.",
         "ex":  "endDate: { year: 2014, month: 06, day: 25, "
            "hour: 9, minute: 0, second: 0 }"},
        {"arg": "general.startHourRange", "type": PCFGSection,
         "def": None, "req": False,
         "doc": "Specific range within each day can be specified. All "
            "previous hours for each day will be ignored. Contains "
            "three elements: hour, minute, second",
         "ex": "startHourRange: { hour: 0, minute: 0, second: 0}"},
        {"arg": "general.endHourRange", "type": PCFGSection,
         "def": None, "req": False,
         "doc": "A specific range within each day can be specified. "
            "All posterior hours for each day will be ignored. It "
            "contains three elements: hour, minute, second",
         "ex": "endHourRange: { hour: 15, minute: 0, second: 0}"},
        {"arg": "general.timeInterval", "type": int,
         "def": None, "req": False,
         "doc": "A step interval starting from general.startDate. "
            "The interval is in seconds",
         "ex": "timeInterval: 900"},
        {"arg": "general.visualise", "type": bool,
         "def": False, "req": False,
         "doc": "This is mostly for debugging. When True, the pipeline "
            "will pause at each component and visualize the "
            "step. This is discouraged for normal use as it stops "
            "the pipeline.",
         "ex": "visualise: True"},
        {"arg": "general.metas", "type": PCFGSection,
         "def": None, "req": False,
         "doc": "Each element detected in the image will have an id based "
            "on order of detection. This id will be the same for all "
            "images.general.metas allows the customization of this id "
            "into something more relevant. Each element in general.metas "
            "is a dictionary that contains the ImageId / CustomId relation.",
         "ex": "metas:  tlpid : {1: 09A1, 2: 09A2, 3: 09A3, 4: 09A4} "
            "plantid: {1: 16161, 2: 16162, 3: 16163, 4: 16164}"},
        {"arg": "general.inputRootPath", "type": str,
         "def": None, "req": True,
         "doc": "The directory that holds the input Time Stream",
         "ex": "~/Experiments/BVZ0036/BVZ0036-GC02R-C01~fullres-orig"},
        {"arg": "general.outputRootPath", "type": str,
         "def": None, "req": False,
         "doc": "Directory where resulting directories will be put",
         "ex": "outputRootPath: BVZ0036-GC02R-C01~fullres"},
        {"arg": "general.outputPrefix", "type": str,
         "def": None, "req": False,
         "doc": "By default the output will have the same name as the "
            "input directory plus a relevant suffix. This variable "
            "overrides this behavior and uses a custom name. The "
            "output Time Stream suffix is still added.",
         "ex": "outputPrefix: BVZ0036-GC02R-C01~fullres"},
        {"arg": "general.outputPrefixPath", "type": str,
         "def": None, "req": False,
         "doc": "Convenience variable. Should not be set",
         "ex": ""}]
    # Names of the two main subsections
    pipelineStr = "pipeline"
    generalStr = "general"
    outstreamsStr = "outstreams"

    def __init__(self, configFile, depth=2):
        """PCFGConfig houses all configuration options

        The pipeline configuration is made up of three main parts: the pipeline
        list, the general dictionary and the outstream list. Anything that is
        in level 0 not named general, pipeline or outstream will be put in
        general.

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

        confDict = PCFGConfig.loadFromFile(self._configFile)
        tmpSubSec = PCFGConfig.createSection(confDict, self._depth, self._name)

        # Force a zero level of three sub-sections (pipeline,general,outstream)
        if not tmpSubSec.hasSubSecName(PCFGConfig.pipelineStr):
            tmpSubSec.setVal(PCFGConfig.pipelineStr,
                             PCFGSection(PCFGConfig.pipelineStr))
        if not tmpSubSec.hasSubSecName(PCFGConfig.generalStr):
            tmpSubSec.setVal(PCFGConfig.generalStr,
                             PCFGSection(PCFGConfig.generalStr))
        if not tmpSubSec.hasSubSecName(PCFGConfig.outstreamsStr):
            tmpSubSec.setVal(PCFGConfig.outstreamsStr,
                             PCFGListSection(PCFGConfig.outstreamsStr))
        for subSecName in tmpSubSec.listSubSecNames():
            if subSecName != PCFGConfig.pipelineStr and \
                    subSecName != PCFGConfig.generalStr and \
                    subSecName != PCFGConfig.outstreamsStr:
                subSec = tmpSubSec.getVal(subSecName, pop=True)
                tmpSubSec.general.setVal(subSecName, subSec)

        # Equal __subsections to allow instance.element.element....
        self.__dict__["__subsections"] = tmpSubSec.__dict__["__subsections"]

    def append(self, configFile, depth=2, overwrite=False):
        if not os.path.exists(configFile) or not os.path.isfile(configFile):
            raise PCFGExInvalidFile(configFile)
        confDict = PCFGConfig.loadFromFile(configFile)
        tmpSubSec = PCFGConfig.createSection(confDict, depth, "--")

        # Deal with general
        if tmpSubSec.hasSubSecName(PCFGConfig.generalStr):
            for index in tmpSubSec.general.itertree():
                if (self.general.hasSubSecName(index) and overwrite) \
                        or not self.general.hasSubSecName(index):
                    self.general.setVal(index,
                                        tmpSubSec.general.getVal(index,
                                                                 pop=True))
            # Use getVal(pop=True) to remove general
            tmpSubSec.getVal(PCFGConfig.generalStr, pop=True)

        # Deal with outstreams
        if tmpSubSec.hasSubSecName(PCFGConfig.outstreamsStr):
            for index in tmpSubSec.outstreams.itertree():
                if (self.outstreams.hasSubSecName(index) and overwrite) \
                        or not self.outstreams.hasSubSecName(index):
                    self.outstreams.setVal(
                        index, tmpSubSec.outstreams.getVal(index, pop=True))
            # Use getVal(pop=True) to remove outstreams
            tmpSubSec.getVal(PCFGConfig.outstreamsStr, pop=True)

        # Deal with pipeline
        if tmpSubSec.hasSubSecName(PCFGConfig.pipelineStr):
            if overwrite:
                self.pipeline = tmpSubSec.pipeline
            else:
                # pop to remove
                tmpSubSec.getVal(PCFGConfig.pipelineStr, pop=True)

        # Try to find components.
        for plcName in self.pipeline.listSubSecNames():
            plcSec = self.pipeline.getVal(plcName)
            if tmpSubSec.hasSubSecName(plcSec.name):
                tmpSec = tmpSubSec.getVal(plcSec.name, pop=True)
                for index in tmpSec.itertree():
                    if (plcSec.hasSubSecName(index) and overwrite) \
                            or not plcSec.hasSubSecName(index):
                        plcSec.setVal(index, tmpSec.getVal(index,
                                                           pop=True))

        # Set the remaining zero level secs into general. Do not overwrite.
        for index in tmpSubSec.itertree():
            if not self.general.hasSubSecName(index):
                self.general.setVal(index, tmpSubSec.getVal(index, pop=True))

    def validate(self):
        """ Validate __subsections against argNames"""

        for argName in PCFGConfig.argNames:

            try:
                val = self.getVal(argName["arg"])
                if not isinstance(val, argName["type"]):
                    raise PCFGExInvalidType(argName["type"], type(val))

            except PCFGExInvalidSubsection:
                if argName["req"]:
                    # Make sure we have all the required variables
                    raise PCFGExMissingRequiredArgument(argName["arg"])

                # Init defaults when missing
                self.setVal(argName["arg"], argName["def"])

        return True

    def autocomplete(self):
        """ Guess and cast relevant values"""
        # outputRootPath : Directory where resulting directories will be put
        # outputPrefix : Prefix identifying all outputs from this "run"
        # outputPrefixPath : Convenience var. outputRootPath/outputPrefix.
        if not self.general.hasSubSecName("outputRootPath") \
                and self.general.hasSubSecName("inputRootPath"):
            self.general.setVal("outputRootPath",
                                os.path.dirname(self.general.inputRootPath))

        if not self.general.hasSubSecName("outputPrefix") \
                and self.general.hasSubSecName("inputRootPath"):
            irpabs = os.path.abspath(self.general.inputRootPath)
            self.general.setVal("outputPrefix", os.path.basename(irpabs))

        if not self.general.hasSubSecName("outputPrefixPath") \
                and self.general.hasSubSecName("outputRootPath") \
                and self.general.hasSubSecName("outputPrefix"):
            self.general.setVal(
                "outputPrefixPath",
                os.path.join(self.general.outputRootPath,
                             self.general.outputPrefix))

        # FIXME: Casts are inactive becausea JSON not able to handle pyobjects
        dateKeys = ["year", "month", "day", "hour", "minute", "second"]
        if self.general.hasSubSecName("startDate") \
                and not isinstance(self.general.startDate, datetime.datetime):
            sd = self.general.startDate
            if not isinstance(sd, PCFGSection):
                raise PCFGExInvalidType(PCFGSection, type(sd))
            # Check for missing keys
            if False in [x in sd.listSubSecNames() for x in dateKeys]:
                raise PCFGException(
                    "Missing one of {} in startDate".format(dateKeys))
            # sd = datetime.datetime(sd.year, sd.month, sd.day
            #                        sd.hour, sd.minute, sd.second)
            # self.general.startDate = sd

        if self.general.hasSubSecName("endDate") \
                and not isinstance(self.general.endDate, datetime.datetime):
            ed = self.general.endDate
            if not isinstance(ed, PCFGSection):
                raise PCFGExInvalidType(PCFGSection, type(ed))
            # Check for missing keys
            if False in [x in ed.listSubSecNames() for x in dateKeys]:
                raise PCFGException(
                    "Missing one of {} in endDate".format(dateKeys))
            # ed = datetime.datetime(ed.year, ed.month, ed.day, \
            #                        ed.hour, ed.minute, ed.second)
            # self.general.endDate = ed

        timeKeys = ["hour", "minute", "second"]
        if self.general.hasSubSecName("startHourRange") \
                and not isinstance(self.general.startHourRange, datetime.time):
            sr = self.general.startHourRange
            if not isinstance(sr, PCFGSection):
                raise PCFGExInvalidType(PCFGSection, type(sr))
            # Check for missing keys
            if False in [x in sr.listSubSecNames() for x in timeKeys]:
                raise PCFGException(
                    "Missing one of {} in startHourRange".format(timeKeys))
            # sr = datetime.time(sr.hour, sr.minute, sr.second)
            # self.general.startHourRange = sr

        if self.general.hasSubSecName("endHourRange") \
                and not isinstance(self.general.endHourRange, datetime.time):
            er = self.general.endHourRange
            if not isinstance(er, PCFGSection):
                raise PCFGExInvalidType(PCFGSection, type(er))
            # Check for missing keys
            if False in [x in er.listSubSecNames() for x in timeKeys]:
                raise PCFGException(
                    "Missing one of {} in endHourRange".format(timeKeys))
            # er = datetime.time(er.hour, er.minute, er.second)
            # self.general.endHourRange = er

    def __str__(self):
        return "".join(self.listTree(withVals=True, endline="\n"))

    @classmethod
    def info(cls, _str=True):
        if not _str:
            return PCFGConfig.argNames

        # Auto text wrapper to output the doc.
        tw = TextWrapper()
        tw.initial_indent = "    "
        tw.subsequent_indent = "    "

        retVal = "General Configuration: \n"
        for argName in PCFGConfig.argNames:
            arg = str(argName["arg"])
            argreq = str(argName["req"])
            argtype = str(argName["type"].__name__)
            argdef = str(argName["def"])
            argdoc = str(argName["doc"])
            argex = str(argName["ex"])
            doclines = tw.wrap(argdoc)

            aType = "optional"
            if argreq:
                aType = "required"

            retVal += "  %s (%s, %s):\n" % (arg, argtype, aType)
            retVal += "    Defaults to %s\n" % (argdef)
            for docline in doclines:
                retVal += "%s\n" % docline
            retVal += "    Example: %s\n" % argex
            retVal += "\n"
        return retVal

    @classmethod
    def loadFromFile(cls, configFile):
        def loadFromYaml(configFile):
            f = file(configFile)
            yDict = yaml.load(f)
            f.close()
            return yDict

        # To load from another config format create a loadFrom function
        confDict = None
        confLoaded = False
        for func in [loadFromYaml]:
            try:
                confDict = func(configFile)
                confLoaded = True
            except:
                continue
            break

        if not confLoaded:
            raise PCFGExOnLoadConfig(configFile)

        return confDict

    @classmethod
    def createSection(cls, confElems, depth, name):
        """ Initialize configuration sections from dictionary.

        continue recursion when (i) value is dict indexed by str only and (ii)
        is list of name outstreams or pipeline.
        """

        # FIXME: Introduce a new global section called components. Its function
        # is to list components and ignore the order which they appear.
        # Components shall be used when the user wants to add additional config
        # parameters to the components present in pipeline. This is much better
        # than directly listing them in timestream.yml. We create lists only
        # for pipeline or outstreams so we don't have to change the config
        # format.
        retVal = None
        if isinstance(confElems, dict) \
            and False not in [isinstance(x, str)
                              for x in confElems.keys()]:  # all str keys
            retVal = PCFGSection(name)
            inds = confElems.keys()
        elif isinstance(confElems, list) and \
                (name == PCFGConfig.pipelineStr
                 or name == PCFGConfig.outstreamsStr):
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
