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

interval = None
if len(sys.argv) < 5:
    inputRootPathLeft  = '/home/chuong/north1ws/Data/Borevitz/BVZ0018/BVZ0018-GC05L-C01~fullres-30min/BVZ0018-GC05L-C01~fullres-orig-corr'
    inputRootPathRight = '/home/chuong/north1ws/Data/Borevitz/BVZ0018/BVZ0018-GC05R-C01~fullres-30min/BVZ0018-GC05R-C01~fullres-orig-corr'
    inputPotConfig     = '/home/chuong/Data/CVS/BVZ0018_plant_position_new_updated_chamber5.csv'
    outputRootPath     = '/home/chuong/north1ws/Data/Borevitz/BVZ0018/BVZ0018-GC05R-C01~fullres-30min-unr'
else:
    try:
        inputRootPathLeft  = sys.argv[1]
        inputRootPathRight = sys.argv[2]
        inputPotConfig     = sys.argv[3]
        outputRootPath     = sys.argv[4]
        interval           = int(sys.argv[5])
    except:
        pass

timestream.setup_module_logging(level=logging.INFO)
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
            # make sure this match with the format of input CSV file
            potID = int(getTrayPotID(row[0])[1])
            name = row[3]
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

for imgL,imgR in itertools.izip(tsL.iter_by_timepoints(remove_gaps=False, start=start, end=end, interval = None), 
                                tsR.iter_by_timepoints(remove_gaps=False, start=start, end=end, interval = None)):
    if imgL is None or imgL.pixels is None or \
       imgR is None or imgR.pixels is None:
        print('Missing Image')
    else:
        print("Process", imgL.path, '...')
        print("       ", imgR.path, '...')
        datetimeStrL = timestream.parse.ts_format_date(imgL.datetime)
        datetimeStrR = timestream.parse.ts_format_date(imgR.datetime)
        if datetimeStrL != datetimeStrR:
            print("Warning: Image pair is not captured at the same time.")
            
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
                    potID_ = potID
                else:
                    img = imgR.pixels
                    potID_ = potID - 160
                potImg = img[potLoc[1]-potWidth/2: potLoc[1]+potWidth/2, potLoc[0]-potWidth/2: potLoc[0]+potWidth/2, :]
                updateDicBins(potImgDic, name, potImg)
        
        imgDerandon = np.zeros([imgHeight, imgWidth, 3], dtype = imgL.pixels.dtype)
        for i,name in enumerate(plantList):
            row, col = divmod(i, cols)
            row = row*3 # allow maximum 3 pots per plant
            for j, potImg in enumerate(potImgDic[name]):
                if j < 3:
                    imgDerandon[(row+j)*potWidth: (row+j+1)*potWidth, col*potWidth: (col+1)*potWidth, :] = potImg

        lineThickness = 5 #pixels
        for row in range(rows):
            if row == 0:
                continue
            imgDerandon[3*row*potWidth-lineThickness/2:3*row*potWidth+lineThickness/2,:,:] = 255
        for col in range(cols):
            if col == 0:
                continue
            imgDerandon[:,col*potWidth-lineThickness/2:col*potWidth+lineThickness/2,:] = 255
        # clear the empty region
        row, col = divmod(len(plantList), cols)
        imgDerandon[3*(row)*potWidth+lineThickness/2:-1, col*potWidth+lineThickness/2:-1, :] = 0

        textThickness = 5 #pixels
        fontScale = 2 # tiems the font's base size
        font = cv2.FONT_HERSHEY_SIMPLEX
        fontBaseSize = 20 # pixel
        for i,name in enumerate(plantList):
            row, col = divmod(i, cols)
            row = row*3 # allow maximum 3 pots per plant
            pos = (int((col+0.5)*potWidth) - int(len(name)*fontScale*fontBaseSize/2.0), int((row+2.9)*potWidth))
            cv2.putText(imgDerandon, name, pos, font, fontScale, (255,255,255), thickness = textThickness)


        img = timestream.TimeStreamImage()
        img.datetime = imgL.datetime
        img.pixels = imgDerandon
        ts_out.write_image(img)
        ts_out.write_metadata()
        
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


