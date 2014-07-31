# -*- coding: utf-8 -*-
"""
Created on Wed Jul 23 11:01:22 2014

@author: chuong nguyen, chuong.v.nguyen@gmail.com
"""
from __future__ import absolute_import, division, print_function

import timestream
import matplotlib.pylab as plt
import csv
import math
import numpy as np
import cv2
import logging
import sys, os
import itertools

def getTrayPotID(code, traysPerChamber = 8, gridSize = [5,4]):
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


def getTimestream(inputRootPathLeft, inputRootPathRight, inputPotConfig, chamberID):
    tsL = timestream.TimeStream()
    tsL.load(inputRootPathLeft)
    tsR = timestream.TimeStream()
    tsR.load(inputRootPathRight)
    
    for attr in timestream.parse.validate.TS_MANIFEST_KEYS:
        print("   tsL.%s:" % attr, getattr(tsL, attr))
    for attr in timestream.parse.validate.TS_MANIFEST_KEYS:
        print("   tsR.%s:" % attr, getattr(tsR, attr))
    
    ts_out = timestream.TimeStream()
    ts_out.create(outputRootPath)
    
    plant2PotDic = {}
    plantSet = set()
    # a list of empty plant names in 320 pots of both left & right chamber
    pot2PlantList = ['']*320  
    
    with open(inputPotConfig, 'rb') as csvfile:
        spamreader = csv.reader(csvfile, delimiter=',')
        for i,row in enumerate(spamreader):
            if i == 0:
                print(', '.join(row))
            else:
                if chamberID != row[6]:
                    continue
                # make sure this match with the format of input CSV file
                row7 = row[7]
                if len(row7) == 3:
                    row7 = '0' + row7 # add leading zero
                potID = int(getTrayPotID(row7)[1])
                name = row[2]
                if len(name) == 0:
                    print('empty pot at {}'.format(potID))
                    continue
                
                plantSet.add(name)
                updateDicBins(plant2PotDic, name, potID)
                    
                if len(pot2PlantList[potID-1]) == 0:
                    pot2PlantList[potID-1] = name
                else:
                    print('### Error: found {} in the same pot with {}'.format(name, pot2PlantList[potID-1]))
    
    plantList = list(plantSet)
    plantList.sort()
    print(len(plantList))
    print(plantList)
    
    potWidth = 250 # pixels
    potsPerPlant = 3
    noPlants = len(plantList)
    
    AR = [9, 16]
    AR2 = [AR[0]/potsPerPlant, AR[1]]
    cols = int(round(math.sqrt(noPlants*AR2[1]/AR2[0])))
    rows = int(round(noPlants/cols))
    imgWidth  = cols*potWidth
    imgHeight = rows*potWidth*potsPerPlant
    print(noPlants, rows*cols)
    print(imgWidth, imgHeight, imgWidth/imgHeight, 16/9)
    
    startL=getattr(tsL, "start_datetime")
    startR=getattr(tsR, "start_datetime")
    endL = getattr(tsL, "end_datetime")
    endR = getattr(tsR, "end_datetime")
    if startL > startR:
        start = startL
    else:
        start = startR
    if endL < endR:
        end = endL
    else:
        end = endR
    print(start, end)
    return tsL, tsR, start, end, plant2PotDic, plantSet, pot2PlantList, plantList

def extractPot(tsL, tsR, imgL, imgR):
    datetimeStrL = timestream.parse.ts_format_date(imgL.datetime)
    datetimeStrR = timestream.parse.ts_format_date(imgR.datetime)
    # TODO: use previous pot data if this is missing
    potLocsChamberL = tsL.image_data[datetimeStrL]['potLocs']
    potLocsChamberR = tsR.image_data[datetimeStrR]['potLocs']
    
    potLocListL = []
    potLocListR = []
    for potLocsTrayL,potLocsTrayR in zip(potLocsChamberL, potLocsChamberR):
        for potLocL,potLocR in zip(potLocsTrayL,potLocsTrayR):
            potLocListL.append(potLocL)
            potLocListR.append(potLocR)
    potLocList = potLocListL + potLocListL      
    
    potImgDic = {}
    for name in plantList:
        for potID in plant2PotDic[name]:
            potLoc = potLocList[potID-1]
            if potID <= 160:
                img = imgL.pixels
            else:
                img = imgR.pixels
            potImg = img[potLoc[1]-potWidth/2: potLoc[1]+potWidth/2, potLoc[0]-potWidth/2: potLoc[0]+potWidth/2, :]
            updateDicBins(potImgDic, name, potImg)
    return potImgDic

#if len(sys.argv) < 5:
#    inputRootPathLeft  = '/home/chuong/north1ws/Data/Borevitz/BVZ0018/BVZ0018-GC05L-C01~fullres-30min/BVZ0018-GC05L-C01~fullres-orig-corr'
#    inputRootPathRight = '/home/chuong/north1ws/Data/Borevitz/BVZ0018/BVZ0018-GC05R-C01~fullres-30min/BVZ0018-GC05R-C01~fullres-orig-corr'
#    inputPotConfig     = '/home/chuong/Data/CVS/BVZ0036-traitcapture-db-import.csv'
#    outputRootPath     = '/home/chuong/north1ws/Data/Borevitz/BVZ0018/BVZ0018-GC05B-C01~fullres-30min-unr'
#else:
#    try:
#        inputRootPathLeft  = sys.argv[1]
#        inputRootPathRight = sys.argv[2]
#        inputPotConfig     = sys.argv[3]
#        outputRootPath     = sys.argv[4]
#        interval           = int(sys.argv[5])
#    except:
#        pass

inputPotConfig     = '/home/chuong/Data/CVS/BVZ0036-traitcapture-db-import.csv'
chamberIDs = ['GC02', 'GC05']
chambers = {}
chambers['GC02'] = {}
chambers['GC05'] = {}
#chambers['GC02']['leftChamberRootPath']  = '/home/chuong/Data/Borevitz/BVZ0036/BVZ0036-GC02L-C01~fullres-30min/BVZ0036-GC02L-C01~fullres-orig-corr'
#chambers['GC02']['rightChamberRootPath'] = '/home/chuong/Data/Borevitz/BVZ0036/BVZ0036-GC02R-C01~fullres-30min/BVZ0036-GC02R-C01~fullres-orig-corr'
#chambers['GC05']['leftChamberRootPath']  = '/home/chuong/Data/Borevitz/BVZ0036/BVZ0036-GC05L-C01~fullres-30min/BVZ0036-GC05L-C01~fullres-orig-corr'
#chambers['GC05']['rightChamberRootPath'] = '/home/chuong/Data/Borevitz/BVZ0036/BVZ0036-GC05R-C01~fullres-30min/BVZ0036-GC05R-C01~fullres-orig-corr'
#outputRootPath = '/home/chuong/Data/Borevitz/BVZ0036/BVZ0036-GC02+05B-C01~fullres-30min-unr'
chambers['GC02']['leftChamberRootPath']  = '/home/chuong/north1ws/Data/Borevitz/BVZ0036/BVZ0036-GC02L-C01~fullres-30min/BVZ0036-GC02L-C01~fullres-orig-corr'
chambers['GC02']['rightChamberRootPath'] = '/home/chuong/north1ws/Data/Borevitz/BVZ0036/BVZ0036-GC02R-C01~fullres-30min/BVZ0036-GC02R-C01~fullres-orig-corr'
chambers['GC05']['leftChamberRootPath']  = '/home/chuong/north1ws/Data/Borevitz/BVZ0036/BVZ0036-GC05L-C01~fullres-30min/BVZ0036-GC05L-C01~fullres-orig-corr'
chambers['GC05']['rightChamberRootPath'] = '/home/chuong/north1ws/Data/Borevitz/BVZ0036/BVZ0036-GC05R-C01~fullres-30min/BVZ0036-GC05R-C01~fullres-orig-corr'
outputRootPath = '/home/chuong/north1ws/Data/Borevitz/BVZ0036/BVZ0036-GC02+05B-C01~fullres-30min-unr-sel'

timestream.setup_module_logging(level=logging.INFO)

for chamberID in chamberIDs:
    outputs = getTimestream(chambers[chamberID]['leftChamberRootPath'], 
                            chambers[chamberID]['rightChamberRootPath'], 
                            inputPotConfig, chamberID)
    tsL, tsR, start, end, plant2PotDic, plantSet, pot2PlantList, plantList = outputs

    chambers[chamberID]['leftChamberTS' ] = tsL
    chambers[chamberID]['rightChamberTS'] = tsR
    chambers[chamberID]['start']          = start
    chambers[chamberID]['end']            = end
    chambers[chamberID]['plant2PotDic']   = plant2PotDic
    chambers[chamberID]['plantSet']       = plantSet
    chambers[chamberID]['pot2PlantList']  = pot2PlantList
    chambers[chamberID]['plantList']      = plantList

for chamberID in ['GC02', 'GC05']:
    for tsID in ['leftChamberTS', 'rightChamberTS']:
        for attr in timestream.parse.validate.TS_MANIFEST_KEYS:
            print("   ts_%s_%s.%s:" % (chamberID, tsID, attr), getattr(chambers[chamberID][tsID], attr))

ts_out = timestream.TimeStream()
ts_out.create(outputRootPath)


potWidth = 250 # pixels
potsPerPlant = 3
noChambers = len(chamberIDs)
noPlants = len(plantList)

AR = [9, 16]
AR2 = [AR[0]/potsPerPlant, AR[1]/noChambers]
cols = int(math.ceil(math.sqrt(noPlants*AR2[1]/AR2[0])))
rows = int(math.ceil(noPlants/cols))
imgWidth  = potWidth*cols*noChambers
imgHeight = potWidth*rows*potsPerPlant
print(noPlants, rows*cols)
print(imgWidth, imgHeight, imgWidth/imgHeight, 16/9)

start0=chambers['GC02']['start' ]
start1=chambers['GC05']['start']
end0 = chambers['GC02']['end' ]
end1 = chambers['GC05']['end' ]
if start0 > start1:
    start = start0
else:
    start = start1
if end0 < end1:
    end = end0
else:
    end = end1
print(start, end)

#iterators = ()
#for chamberID in ['GC02', 'GC05']:
#    for tsID in ['leftChamberTS', 'rightChamberTS']:
#        iterators = iterators + (chambers[chamberID][tsID ].iter_by_timepoints(remove_gaps=False, start=start, end=end, interval = None),)

windowName = 'Derandomised image'
cv2.moveWindow(windowName, 10,10)        
for img0L,img0R,img1L,img1R in itertools.izip(chambers['GC02']['leftChamberTS' ].iter_by_timepoints(remove_gaps=False, start=start, end=end, interval = None),
                                              chambers['GC02']['rightChamberTS'].iter_by_timepoints(remove_gaps=False, start=start, end=end, interval = None),
                                              chambers['GC05']['leftChamberTS' ].iter_by_timepoints(remove_gaps=False, start=start, end=end, interval = None),
                                              chambers['GC05']['rightChamberTS'].iter_by_timepoints(remove_gaps=False, start=start, end=end, interval = None)):
    
    if img0L is None or img0L.pixels is None or \
       img0R is None or img0R.pixels is None or \
       img1L is None or img1L.pixels is None or \
       img1R is None or img1R.pixels is None:
        print('Missing Image')
    else:
        print("Process", img0L.path, '...')
        print("       ", img0R.path, '...')
        print("       ", img1L.path, '...')
        print("       ", img1R.path, '...')
        chambers['GC05']['rightImage'] = img1R.datetime
        datetimeStr0L = timestream.parse.ts_format_date(img0L.datetime)
        datetimeStr0R = timestream.parse.ts_format_date(img0R.datetime)
        datetimeStr1L = timestream.parse.ts_format_date(img1L.datetime)
        datetimeStr1R = timestream.parse.ts_format_date(img1R.datetime)
        if datetimeStr0L != datetimeStr0R or datetimeStr0L != datetimeStr1L or datetimeStr1L != datetimeStr1R:
            print("Warning: Image pair is not captured at the same time.")

        if datetimeStr0L not in chambers['GC02']['leftChamberTS' ].image_data.keys():
               print("Cannot find time stamp " + datetimeStr0L + " in timestream 0")
               continue
        if datetimeStr0R not in chambers['GC02']['rightChamberTS'].image_data.keys():
               print("Cannot find time stamp " + datetimeStr0L + " in timestream 1")
               continue
        if datetimeStr1L not in chambers['GC05']['leftChamberTS' ].image_data.keys():
               print("Cannot find time stamp " + datetimeStr0L + " in timestream 2")
               continue
        if datetimeStr1R not in chambers['GC05']['rightChamberTS'].image_data.keys():
               print("Cannot find time stamp " + datetimeStr0L + " in timestream 3")
               continue
        
        potImgDicList = [extractPot(chambers['GC02']['leftChamberTS' ], 
                                    chambers['GC02']['rightChamberTS'], 
                                    img0L, img0R),
                         extractPot(chambers['GC05']['leftChamberTS' ], 
                                    chambers['GC05']['rightChamberTS'], 
                                    img1L, img1R)]
        
        imgDerandon = np.zeros([imgHeight, imgWidth, 3], dtype = img0L.pixels.dtype)
        for i,name in enumerate(plantList):
            row, col = divmod(i, cols)
            row = row*potsPerPlant
            col = col*noChambers
            for k,potImgDic in enumerate(potImgDicList):
                for j, potImg in enumerate(potImgDic[name]):
                    if j < potsPerPlant:
                        imgDerandon[(row+j)*potWidth: (row+j+1)*potWidth, (col+k)*potWidth: (col+k+1)*potWidth, :] = potImg
                    else:
                        print("There are more than {} pots for {} ({} pots).".format(potsPerPlant, name, len(potImgDic[name])))
                        break

        lineThickness = 5 #pixels
        for row in range(rows):
            if row == 0:
                continue
            imgDerandon[potsPerPlant*row*potWidth-lineThickness/2:potsPerPlant*row*potWidth+lineThickness/2,:,:] = 255
        for col in range(cols):
            if col == 0:
                continue
            imgDerandon[:,noChambers*col*potWidth-lineThickness/2:noChambers*col*potWidth+lineThickness/2,:] = 255
        # clear the empty region
        row, col = divmod(len(plantList), cols)
        imgDerandon[potsPerPlant*(row)*potWidth+lineThickness/2:-1, noChambers*col*potWidth+lineThickness/2:-1, :] = 0

        textThickness = 5 #pixels
        fontScale = 2 # tiems the font's base size
        font = cv2.FONT_HERSHEY_SIMPLEX
        fontBaseSize = 20 # pixel
        for i,name in enumerate(plantList):
            row, col = divmod(i, cols)
            row = row*potsPerPlant
            col = col*noChambers
            pos = (int((col+noChambers/2.0)*potWidth) - int(len(name)*fontScale*fontBaseSize/2.0), int((row+potsPerPlant-0.1)*potWidth))
            cv2.putText(imgDerandon, name, pos, font, fontScale, (255,255,255), thickness = textThickness)


        img = timestream.TimeStreamImage()
        img.datetime = img0L.datetime
        img.pixels = imgDerandon
        ts_out.write_image(img)
        ts_out.write_metadata()
        
        scale = img.pixels.shape[0]//1000 + 1
        imgResized = cv2.resize(img.pixels, (img.pixels.shape[1]//scale, img.pixels.shape[0]//scale))
        timestamp = timestream.parse.ts_format_date(img.datetime)
        cv2.putText(imgResized, timestamp, (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), thickness = 1)
        cv2.imshow(windowName, imgResized[:,:,::-1])
        k = cv2.waitKey(1000)
        if k == 1048603:
            # escape key is pressed
            break

#        figL = plt.figure()
#        plt.imshow(imgL.pixels)
#        figL.hold(True)
#        figR = plt.figure()
#        plt.imshow(imgR.pixels)
#        figR.hold(True)
##        for name in plantList:
##            for potID in plant2PotDic[name]:
##                potLoc = potLocList[potID-1]
##                if potID <= 160:
##                    plt.figure(figL.number)
##                else:
##                    plt.figure(figR.number)
##                plt.text(potLoc[0], potLoc[1], str(potID) + '\n' +  name, color='red')

#        plt.figure()
#        plt.imshow(imgDerandon)
##        plt.xlim([0, imgDerandon.shape[1]])
##        plt.ylim([0, imgDerandon.shape[0]])
##        plt.gca().invert_yaxis()
##        plt.hold(True)
##        for i,name in enumerate(plantList):
##            row, col = divmod(i, cols)
##            row = row*3 # allow maximum 3 pots per plant
##            plt.text((col+0.5)*potWidth, (row+2.8)*potWidth, name, color='red', horizontalalignment='center')
##            plt.plot([col*potWidth, col*potWidth, (col+1)*potWidth, (col+1)*potWidth, col*potWidth], 
##                     [row*potWidth, (row+3)*potWidth, (row+3)*potWidth, row*potWidth, row*potWidth], 'b')
#        plt.show()


