# -*- coding: utf-8 -*-
"""
Created on Wed Aug 13 14:25:45 2014

@author: chuong nguyen
"""
import sys, os, glob, shutil

def separateTimeStamp(FileNameList, TimeStampLength = 22):
    NamePrefixList = []
    TimeStampStrList = []
    ExtensionList = []
    for FileName in FileNameList:
        FileName2 = os.path.basename(FileName)
        Extension = os.path.splitext(FileName2)[1]
        NamePrefix = FileName2[:-(TimeStampLength+len(Extension))]
        if NamePrefix[-1] == '_':
            NamePrefix = NamePrefix[:-1]
        TimeStampStr = FileName2[-(TimeStampLength+len(Extension)):-(len(Extension))]
        NamePrefixList.append(NamePrefix)
        TimeStampStrList.append(TimeStampStr)
        ExtensionList.append(Extension)
    return NamePrefixList, TimeStampStrList, ExtensionList

def createTimeStreamPaths(RootPath, PathList, createNew = True):
    FullPathList = []
    for path in PathList:
        FullPath = os.path.join(RootPath, path)
        FullPathList.append(FullPath)
    return FullPathList

def saveToTimeStream(FileNameList, NamePrefixList, TimeStampList, RootPath):
    for FileName, NamePrefix, TimeStampStr in zip(FileNameList, NamePrefixList, TimeStampStrList):
        # create timestream folder
        TSPath    = os.path.join(RootPath, NamePrefix)
        YearPath  = os.path.join(TSPath, TimeStampStr[:4])
        MonthPath = os.path.join(YearPath, TimeStampStr[:7])
        DayPath   = os.path.join(MonthPath, TimeStampStr[:10])
        if not os.path.exists(DayPath):
            os.makedirs(DayPath)

        # copy the file over if doesn't exist
        NewFile = os.path.join(DayPath, os.path.basename(FileName))
        if not os.path.exists(NewFile):
            print('Copy {} \nto {}'.format(FileName, DayPath))
            shutil.copyfile(FileName, NewFile)
        else:
            print('File {} exists.'.format(NewFile))

if len(sys.argv) < 3:
    RawPath = '/home/chuong/Data/phenocam/a_data/TimeStreams/Borevitz/BVZ0038/_data/BVZ0038-PhenotypeData'
    RootPath = '/home/chuong/Data/phenocam/a_data/TimeStreams/Borevitz/BVZ0038/_data/BVZ0038-PlantTS'
    #RootPath = '/home/chuong/Data/BVZ0038-PlantTS'
else:
    RawPath = sys.argv[1]
    RootPath = sys.argv[2]

day_interval = 2
starDate = [2014, 8, 5] # [year, month, day]
TimeStreamPathSet = ()
for i in range(0, 30, day_interval):
    path = str(starDate[0]) + '_' + str(starDate[1]) + '_' + str(starDate[2]+i)
    path = os.path.join(RawPath, path)
    if os.path.exists(path):
        print('Process ' + path)
        FileNameList = glob.glob(os.path.join(path, '*.jpg'))
        NamePrefixList, TimeStampStrList, ExtensionList = separateTimeStamp(FileNameList, TimeStampLength = 22)
        saveToTimeStream(FileNameList, NamePrefixList, TimeStampStrList, RootPath)