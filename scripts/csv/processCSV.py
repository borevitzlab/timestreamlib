# -*- coding: utf-8 -*-
"""
Created on Wed Nov  5 11:12:52 2014

@author: chuong
"""
from __future__ import print_function
import sys
import glob
import os
import csv
import datetime
import time
import numpy as np
import matplotlib.pylab as plt
from timestream.parse import ts_parse_date
import matplotlib.dates as mdates


def getTrayPotID(code, traysPerChamber=8, gridSize=[5, 4]):
    if len(code) != 4:
        print('wrong input')
        return None
    globalTrayID = int(code[:2])

    rowID = ord(code[2].lower()) - ord('a')
    colID = int(code[3])
    inTrayPotID = colID + rowID*gridSize[0]
    potsPerTray = gridSize[0]*gridSize[1]
    globalPotID = (globalTrayID-1)*potsPerTray + inTrayPotID

    return globalTrayID, globalPotID


def updateDicBins(dic, key, value):
    if key not in dic.keys():
        dic[key] = [value]
    else:
        dic[key].append(value)


def readTimeStampDataCSV(CSVFile, StartDate, EndDate):
    TimestampStart = ts_parse_date(StartDate)
    TimestampeEnd = ts_parse_date(EndDate)
    with open(CSVFile, 'rb') as csvfile:
        CsvReader = csv.reader(csvfile, delimiter=',')
        Data = []
        DateList = []
        PotIndex = []
        for i, Row in enumerate(CsvReader):
            if i == 0:
                PotIndex = [int(Num) for Num in Row[1:]]
            else:
                Timestamp = ts_parse_date(Row[0][:19])
                if Timestamp.date() >= TimestampStart.date() and \
                        Timestamp.date() <= TimestampeEnd.date():
                    if Row[-1] == "Na":
                        Row[-1] = "NaN"
                    DataRow = [float(Num) for Num in Row[1:]]
                    Data.append(DataRow)
                    DateList.append(Timestamp)
        return Data, DateList, PotIndex


def readPlantNamePots(inputPotConfig, ChamberNames):
    PlantPotDic = {}
    for ChamberName in ChamberNames:
        PlantPotDic[ChamberName] = {"Plant2PotDic": {}, "PlantIDs": [],
                                    "PlantNames": [],
                                    "PotIndex2Plant": ['']*320}
    with open(inputPotConfig, 'rb') as csvfile:
        spamreader = csv.reader(csvfile, delimiter=',')
        for i, row in enumerate(spamreader):
            if i == 0:
                continue
            else:
                if len(row[7]) > 0:
                    ChamberName = row[7]
                PlantIDs = PlantPotDic[ChamberName]["PlantIDs"]
                PlantNames = PlantPotDic[ChamberName]["PlantNames"]
                PotIndex2Plant = PlantPotDic[ChamberName]["PotIndex2Plant"]
                Plant2PotDic = PlantPotDic[ChamberName]["Plant2PotDic"]

                PlantIDs.append(row[0])
                PlantName = row[3]
                if len(PlantName) > 0:
                    PlantNames.append(PlantName)
                else:
                    PlantNames.append("Empty Pot")
                    continue

                # make sure this match with the format of input CSV file
                row8 = row[8]
                if len(row8) == 3:
                    row8 = '0' + row8  # add leading zero
                ChamberTrayID, ChamberPotIndex = getTrayPotID(row8)

                updateDicBins(Plant2PotDic, PlantName, ChamberPotIndex)

                if len(PotIndex2Plant[ChamberPotIndex-1]) == 0:
                    PotIndex2Plant[ChamberPotIndex-1] = PlantName
                else:
                    print('### Error: found {} in the same pot with {}'.format(
                        PlantName, PotIndex2Plant[ChamberPotIndex-1]))

    return PlantPotDic

#RootPath = "/home/chuong/percy/Data/BVZ0036"
RootPath = "/home/chuong/Data/BVZ0036"
Exp = "BVZ0036"
Chambers = ["GC02", "GC05"]
Conditions = ["Coastal (Wollongong)", "Inland (Goulburn)"]
LineTypes = ["r", "b"]
Sides = ["L", "R"]
Affix = "C01~fullres"
Features = ["area", "compactness", "eccentricity", "perimeter", "roundness",
            "leafcount1"]
FeatureLabels = ["Areas [pixels]", "Compactness", "Eccentricity",
                 "Perimeters [pixels]", "Roundness", "Leaf counts"]
EmptyPots = range(0, 160, 25) + [120]
StartDate = "2014_06_25_00_00_00"
EndDate = "2014_07_24_00_00_00"
# load plant names and positions
PlantNamePotFile = os.path.join(RootPath,
                                "BVZ0036-traitcapture-db-import.csv")
PlantPotDic = readPlantNamePots(PlantNamePotFile, Chambers)

plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d/%Y'))
for i, Feature in enumerate(Features):
    for j, Chamber in enumerate(Chambers):
        ArrayDataList = []
        PotIndexList = []
        for Side in Sides:
            Name = Exp + "-" + Chamber + Side + "-" + Affix
            CSVFile = os.path.join(RootPath, Name + "-csv",
                                   Name + "-" + Feature + ".csv")
            print("Read file {}".format(CSVFile))
            Data, DateList, PotIndex = \
                readTimeStampDataCSV(CSVFile, StartDate, EndDate)
            ArrayData = np.array(Data)

            # remove data at empty pots
            for EmptyPot in EmptyPots:
                ArrayData[:, EmptyPot] = np.nan

            ArrayDataList.append(ArrayData)
            PotIndex = [Index + len(PotIndex) for Index in PotIndex]
            PotIndexList.append(PotIndex)
        ChamberArrayData = np.concatenate(tuple(ArrayDataList), axis=1)

        # Average of all pots
        y = range(ArrayData.shape[0])
        std = range(ArrayData.shape[0])
        for k in range(ArrayData.shape[0]):
            row = ArrayData[k, :]
            NotNan = row[np.invert(np.isnan(row))]
            if len(NotNan) > 0:
                y[k] = np.mean(NotNan)
                std[k] = np.std(NotNan)
            else:
                y[k] = np.nan
                std[k] = np.nan

        if True:  # plot the first pot
            PotIndex = 2
            y = ArrayData[:, PotIndex]
            plt.plot(DateList, y, label=Conditions[j] + ", pot {}".format(PotIndex))
        elif True:  # plot a mean plot
            plt.plot(DateList, y, LineTypes[j], label=Conditions[j])
        else:  # plot all
            plt.plot(DateList, ArrayData, LineTypes[j])

        plt.gcf().autofmt_xdate()
        plt.legend(loc="upper center")
    plt.ylabel(FeatureLabels[i])
    plt.show()
