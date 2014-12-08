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
.. module:: timestream.manipulate.correct_detect
    :platform: Unix, Windows
    :synopsis: Image correction and feature detection

.. moduleauthor:: Chuong Nguyen, Joel Granados
"""

from __future__ import absolute_import, division
import cv2
import logging
import warnings
import matplotlib.pylab as plt
import numpy as np
from scipy import optimize

__author__  = 'Chuong Nguyen'

LOG = logging.getLogger("timestreamlib")


# RED GRN BLU
CameraTrax_24ColorCard = \
    [[115., 196., 91., 94., 129., 98., 223., 58., 194., 93., 162., 229.,
      49., 77., 173., 241., 190., 0., 242., 203., 162., 120., 84., 50.],
     [83., 147., 122., 108., 128., 190., 124., 92., 82., 60., 190., 158.,
      66., 153., 57., 201., 85., 135., 243., 203., 163., 120., 84., 50.],
     [68., 127., 155., 66., 176., 168., 47., 174., 96., 103., 62., 41.,
      147., 71., 60., 25., 150., 166., 245., 204., 162., 120., 84., 52.]]
CameraTrax_24ColorCard180deg = \
    [[50., 84., 120., 162., 203., 242., 0., 190., 241., 173., 77., 49.,
      229., 162., 93., 194., 58., 223., 98., 129., 94., 91., 196., 115.],
     [50., 84., 120., 163., 203., 243., 135., 85., 201., 57., 153., 66.,
      158., 190., 60., 82., 92., 124., 190., 128., 108., 122., 147., 83.],
     [52., 84., 120., 162., 204., 245., 166., 150., 25., 60., 71., 147.,
      41., 62., 103., 96., 174., 47., 168., 176., 66., 155., 127., 68.]]


def getRectCornersFrom2Points(Image, Points, AspectRatio, Rounded=False):
    Length = np.sqrt((Points[0][0] - Points[1][0]) ** 2 +
                     (Points[0][1] - Points[1][1]) ** 2)
    Height = Length / np.sqrt(1 + AspectRatio ** 2)
    Width = Height * AspectRatio
    Centre = np.asarray(
        [Points[0][0] + Points[1][0],
         Points[0][1] + Points[1][1]]) / 2.0
    Angle = np.arctan2(Height, Width) - \
        np.arctan2(
            Points[1][1] - Points[0][1],
            Points[1][0] - Points[0][0])
    InitRect = createRectangle(Centre, Width, Height, Angle)
    CornerTypes = ['topleft', 'bottomleft', 'bottomright', 'topright']
    Rect = []
    if not Rounded:
        for Corner, Type in zip(InitRect, CornerTypes):
            Corner = findCorner(Image, Corner, Type)
            Rect.append(Corner)
    else:
        Rect = findRoundedCorner(Image, InitRect)
    return Rect


def createRectangle(Centre, Width, Height, Angle):
    tl2 = np.asarray([-Width, -Height]) / 2.0
    bl2 = np.asarray([-Width, Height]) / 2.0
    br2 = np.asarray([Width, Height]) / 2.0
    tr2 = np.asarray([Width, -Height]) / 2.0
    RectFit = [tl2, bl2, br2, tr2]
    for i in range(len(RectFit)):
        # rotate around center
        # TODO: comment on how this works mathematically
        xrot = RectFit[i][0] * np.cos(Angle) + RectFit[i][1] * np.sin(Angle)
        yrot = -RectFit[i][0] * np.sin(Angle) + RectFit[i][1] * np.cos(Angle)
        RectFit[i][0], RectFit[i][1] = (xrot + Centre[0]), (yrot + Centre[1])
    return RectFit


def getRectangleParamters(Rect):
    tl = np.asarray(Rect[0])
    bl = np.asarray(Rect[1])
    br = np.asarray(Rect[2])
    tr = np.asarray(Rect[3])

    # paramters of fitted Rectangle
    Centre = (tl + bl + br + tr) / 4.0
    Width = (np.linalg.norm(tr - tl) + np.linalg.norm(br - bl)) / 2.0
    Height = (np.linalg.norm(bl - tl) + np.linalg.norm(br - tr)) / 2.0
    # TODO: this angle calc FAR too complex for one line. Split it & comment
    # how the math works.
    Angle = (np.arctan2(-(tr[1] - tl[1]), tr[0] - tl[0]) +
             np.arctan2(-(br[1] - bl[1]), br[0] - bl[0]) +
             np.arctan2(bl[0] - tl[0], bl[1] - tl[1]) +
             np.arctan2(br[0] - tr[0], br[1] - tr[1])) / 4
    return Centre, Width, Height, Angle


def findCorner(Image, Corner, CornerType='topleft', WindowSize=100,
               Threshold=50):
    x, y = Corner
    half_winsz = int(WindowSize / 2)
    xStart = max(0, x - half_winsz)
    xEnd = min(Image.shape[0], x + half_winsz + 1)
    yStart = max(0, y - half_winsz)
    yEnd = min(Image.shape[1], y + half_winsz + 1)
    window = Image[yStart:yEnd, xStart:xEnd, :].astype(np.float)
    foundLfEdgeX = False
    foundRtEdgeX = False
    foundTpEdgeY = False
    foundBtEdgeY = False

    # Horizontal window size
    hwinsz = window.shape[1] // 2
    for i in range(hwinsz):
        diff0 = np.sum(np.abs(window[hwinsz, hwinsz-i, :] -
                              window[hwinsz, hwinsz, :]))
        diff1 = np.sum(np.abs(window[hwinsz, hwinsz+i, :] -
                              window[hwinsz, hwinsz, :]))
        if diff0 > Threshold and not foundLfEdgeX:
            xLfNew = x - i
            foundLfEdgeX = True
        elif diff1 > Threshold and not foundRtEdgeX:
            xRtNew = x + i
            foundRtEdgeX = True

    # Vertical window size
    vwinsz = window.shape[0] // 2
    for i in range(vwinsz):
        diff2 = np.sum(np.abs(window[vwinsz-i, vwinsz, :] -
                              window[vwinsz, vwinsz, :]))
        diff3 = np.sum(np.abs(window[vwinsz+i, vwinsz, :] -
                              window[vwinsz, vwinsz, :]))
        if diff2 > Threshold and not foundTpEdgeY:
            yTpNew = y - i
            foundTpEdgeY = True
        elif diff3 > Threshold and not foundBtEdgeY:
            yBtNew = y + i
            foundBtEdgeY = True

    if CornerType.lower() == 'topleft' and foundLfEdgeX and foundTpEdgeY:
        return [xLfNew, yTpNew]
    elif CornerType.lower() == 'bottomleft' and foundLfEdgeX and foundBtEdgeY:
        return [xLfNew, yBtNew]
    elif CornerType.lower() == 'bottomright' and foundRtEdgeX and foundBtEdgeY:
        return [xRtNew, yBtNew]
    elif CornerType.lower() == 'topright' and foundRtEdgeX and foundTpEdgeY:
        return [xRtNew, yTpNew]
    else:
        LOG.warn('Cannot detect corner ' + CornerType)
        return [x, y]


def findRoundedCorner(Image, InitRect, searchDistance=20, Threshold=20):
    # TODO: add search for rounded corner with better accuracy
    [topLeft, _, bottomRight, _] = InitRect
    initPot = np.double(Image[topLeft[1]:bottomRight[1],
                              topLeft[0]:bottomRight[0], :])
    foundLeftEdgeX = False
    foundRightEdgeX = False
    foundTopEdgeY = False
    foundBottomEdgeY = False
    for i in range(searchDistance):
        diff0 = np.mean(np.abs(initPot[:, 0, :] - initPot[:, i, :]))
        diff1 = np.mean(np.abs(initPot[:, -1, :] - initPot[:, -i-1, :]))
        diff2 = np.mean(np.abs(initPot[0, :, :] - initPot[i, :, :]))
        diff3 = np.mean(np.abs(initPot[-1, :, :] - initPot[-i-1, :, :]))
        if diff0 > Threshold and not foundLeftEdgeX:
            xLeftNew = topLeft[0] + i
            foundLeftEdgeX = True
        elif diff1 > Threshold and not foundRightEdgeX:
            xRightNew = bottomRight[0] - i
            foundRightEdgeX = True
        if diff2 > Threshold and not foundTopEdgeY:
            yTopNew = topLeft[1] + i
            foundTopEdgeY = True
        elif diff3 > Threshold and not foundBottomEdgeY:
            yBottomNew = bottomRight[1] - i
            foundBottomEdgeY = True
    if foundLeftEdgeX and foundRightEdgeX and foundTopEdgeY and foundBottomEdgeY:
        LOG.info('Found pot edges')
        Rect = [[xLeftNew, yTopNew], [xLeftNew, yBottomNew],
                [xRightNew, yBottomNew], [xRightNew, yTopNew]]
        return Rect
    return InitRect


def correctPointOrder(Rect, tolerance=40):
    # find minimum values of x and y
    minX = 10e6
    minY = 10e6
    for i in range(len(Rect[0])):
        if minX > Rect[i][0]:
            minX = Rect[i][0]
        if minY > Rect[i][1]:
            minY = Rect[i][1]
    # separate left and right
    topLeft, bottomLeft, topRight, bottomRight = [], [], [], []
    for i in range(len(Rect[0])):
        if abs(minX - Rect[0][i]) < tolerance:
            if abs(minY - Rect[i][1]) < tolerance:
                topLeft = [Rect[i][0], Rect[i][1]]
            else:
                bottomLeft = [Rect[i][0], Rect[i][1]]
        else:
            if abs(minY - Rect[i][1]) < tolerance:
                topRight = [Rect[i][0], Rect[i][1]]
            else:
                bottomRight = [Rect[i][0], Rect[i][1]]
    if len(topLeft) * len(bottomLeft) * len(topRight) * len(bottomRight) == 0:
        LOG.warn('Cannot find corRect corner order. Change tolerance value.')
        return Rect
    else:
        Rect = [topLeft, bottomLeft, bottomRight, topRight]
        return Rect


def getMedianRectSize(RectList):
    WidthList = []
    HeightList = []
    for Rect in RectList:
        Centre, Width, Height, Angle = getRectangleParamters(Rect)
        WidthList.append(Width)
        HeightList.append(Height)
    MedianWidth = int(sorted(WidthList)[int(len(RectList) / 2)])
    MedianHeight = int(sorted(HeightList)[int(len(RectList) / 2)])
    return MedianWidth, MedianHeight


def rectifyRectImages(Image, RectList, MedianSize):
    Width, Height = MedianSize
    RectifiedCorners = np.float32(
        [[0, 0], [0, Height], [Width, Height], [Width, 0]])
    RectifiedTrayImages = []
    for Rect in RectList:
        Corners = np.float32(Rect)
        M = cv2.getPerspectiveTransform(Corners, RectifiedCorners)
        RectifiedTrayImage = cv2.warpPerspective(Image, M, (Width, Height))
        RectifiedTrayImages.append(RectifiedTrayImage)
    return RectifiedTrayImages


def readValueFromLineYML(line):
    # FIXME: USE REGEX FOR THIS!!!! never write hacky shit like this using raw
    # string operations.
    name = line[:line.index(':')].strip()
    string = line[line.index(':') + 1:].strip()
    if string[0] in '-+.0123456789':
        if '.' in string:
            value = float(string)
        else:
            value = int(string)
    else:
        value = string
    return name, value


def readOpenCVArrayFromYML(myfile):
    line = myfile.readline().strip()
    rname, rows = readValueFromLineYML(line)
    line = myfile.readline().strip()
    cname, cols = readValueFromLineYML(line)
    line = myfile.readline().strip()
    dtname, dtype = readValueFromLineYML(line)
    line = myfile.readline().strip()
    dname, data = readValueFromLineYML(line)
    if rname != 'rows' and cname != 'cols' and dtname != 'dt' \
            and dname != 'data' and '[' in data:
        LOG.error('Error reading YML file')
    elif dtype != 'd':
        LOG.error('Unsupported data type: dt = ' + dtype)
    else:
        if ']' not in data:
            while True:
                line = myfile.readline().strip()
                data = data + line
                if ']' in line:
                    break
        data = data[data.index('[') + 1: data.index(']')].split(',')
        dlist = [float(el) for el in data]
        if cols == 1:
            value = np.asarray(dlist)
        else:
            value = np.asarray(dlist).reshape([rows, cols])
    return value


def yml2dic(filename):
    with open(filename, 'r') as myfile:
        dicdata = {}
        while True:
            line = myfile.readline()
            if not line:
                break
            line = line.strip()
            if len(line) == 0 or line[0] == '#':
                continue
            if ':' in line:
                name, value = readValueFromLineYML(line)
                # if OpenCV array, do extra reading
                if isinstance(value, str) and 'opencv-matrix' in value:
                    value = readOpenCVArrayFromYML(myfile)
                # add parameters
                dicdata[name] = value
    return dicdata


def writeOpenCVArrayToYML(myfile, key, data):
    myfile.write(key + ': !!opencv-matrix\n')
    myfile.write('   rows: %d\n' % data.shape[0])
    myfile.write('   cols: %d\n' % data.shape[1])
    myfile.write('   dt: d\n')
    myfile.write('   data: [')
    datalist = []
    for i in range(data.shape[0]):
        datalist = datalist + [str(num) for num in list(data[i, :])]
    myfile.write(', '.join(datalist))
    myfile.write(']\n')


def dic2yml(filename, dicdata):
    with open(filename, 'w') as myfile:
        myfile.write('%YAML:1.0\n')
        for key in dicdata:
            data = dicdata[key]
            if isinstance(data, np.ndarray):
                writeOpenCVArrayToYML(myfile, key, data)
            elif isinstance(data, str):
                myfile.write(key + ': "%s"\n' % data)
            elif isinstance(data, int):
                myfile.write(key + ': %d\n' % data)
            elif isinstance(data, float):
                myfile.write(key + ': %f\n' % data)
            else:
                LOG.error('Unsupported data: ', data)


def readCalibration(CalibFile):
    parameters = yml2dic(CalibFile)
    SquareSize = parameters['square_size']
    ImageWidth = parameters['image_width']
    ImageHeight = parameters['image_height']
    ImageSize = (ImageWidth, ImageHeight)
    CameraMatrix = parameters['camera_matrix']
    DistCoefs = parameters['distortion_coefficients']
    RVecs = parameters['RVecs']
    TVecs = parameters['TVecs']
    return ImageSize, SquareSize, CameraMatrix, DistCoefs, RVecs, TVecs


def readGeometries(GeometryFile):
    parameters = yml2dic(GeometryFile)
    rotationAngle = parameters['rotationAngle']
    distcorr = bool(parameters['distortionCorrected'])
    cclst = parameters['colorcardList'].tolist()
    cclst2 = []
    for i in range(0, len(cclst), 4):
        cclst2.append([cclst[i], cclst[i + 1], cclst[i + 2], cclst[i + 3]])
    tylst = parameters['trayList'].tolist()
    tylst2 = []
    for i in range(0, len(tylst), 4):
        tylst2.append([tylst[i], tylst[i + 1], tylst[i + 2], tylst[i + 3]])
    ptlst = parameters['potList'].tolist()
    ptlst2 = []
    for i in range(0, len(ptlst), 4):
        ptlst2.append([ptlst[i], ptlst[i + 1], ptlst[i + 2], ptlst[i + 3]])
    return (rotationAngle, distcorr, cclst2, tylst2, ptlst2)


def createMap(Centre, Width, Height, Angle):
    MapX, MapY = np.meshgrid(np.arange(Width), np.arange(Height))
    MapX = MapX - Width / 2.0
    MapY = MapY - Height / 2.0
    MapX2 = MapX * np.cos(Angle) + MapY * np.sin(Angle) + Centre[0]
    MapY2 = -MapX * np.sin(Angle) + MapY * np.cos(Angle) + Centre[1]
    return MapX2.astype(np.float32), MapY2.astype(np.float32)


def getColorcardColors(ccdCapt, GridSize, Show=False):
    GridCols, GridRows = GridSize
    Captured_Colors = np.zeros([3, GridRows * GridCols])
    STD_Colors = np.zeros([GridRows * GridCols])
    SquareSize2 = int(ccdCapt.shape[0] / GridRows)
    HalfSquareSize2 = int(SquareSize2 / 2)
    sampsz = int(0.5 * HalfSquareSize2)
    if Show:
        plt.figure()
        plt.imshow(ccdCapt)
        plt.hold(True)
    for i in range(GridRows * GridCols):
        Row = i // GridCols
        Col = i - Row * GridCols
        rr = Row * SquareSize2 + HalfSquareSize2
        cc = Col * SquareSize2 + HalfSquareSize2
        Captured_R = ccdCapt[rr - sampsz:rr + sampsz, cc - sampsz:cc + sampsz, 0]
        Captured_R = Captured_R.astype(np.float)
        Captured_G = ccdCapt[rr - sampsz:rr + sampsz, cc - sampsz:cc + sampsz, 1]
        Captured_G = Captured_G.astype(np.float)
        Captured_B = ccdCapt[rr - sampsz:rr + sampsz, cc - sampsz:cc + sampsz, 2]
        Captured_B = Captured_B.astype(np.float)
        STD_Colors[i] = np.std(Captured_R) + \
            np.std(Captured_G) + np.std(Captured_B)
        Captured_R = np.median(Captured_R)
        Captured_G = np.median(Captured_G)
        Captured_B = np.median(Captured_B)
        Captured_Colors[0, i] = Captured_R
        Captured_Colors[1, i] = Captured_G
        Captured_Colors[2, i] = Captured_B
        if Show:
            plt.plot(
                [cc - sampsz, cc - sampsz, cc + sampsz, cc + sampsz, cc - sampsz],
                [rr - sampsz, rr + sampsz, rr + sampsz, rr - sampsz, rr - sampsz],
                'w')
    plt.show()
    return Captured_Colors, STD_Colors

# FIXME: can this comment go somewhere more logical. Either inside the function
# it referrs to, or at the top if it referrs to the module

# Using modified Gamma Correction Algorithm by
# Constantinou2013 - A comparison of color correction algorithms for
# endoscopic cameras


def getColorMatchingError(Arg, Colors, Captured_Colors):
    ColorMatrix = Arg[:9].reshape([3, 3])
    ColorConstant = Arg[9:12]
    ColorGamma = Arg[12:15]
    ErrorList = []
    for Color, Captured_Color in zip(Colors, Captured_Colors):
        Color2 = np.dot(ColorMatrix, Captured_Color) + ColorConstant
        Color3 = 255.0 * np.power(Color2 / 255.0, ColorGamma)
        Error = np.linalg.norm(Color - Color3)
        ErrorList.append(Error)
    return ErrorList


def correctColor(Image, ColorMatrix, ColorConstant, ColorGamma):
    ImageCorrected = np.zeros_like(Image)
    for i in range(Image.shape[0]):
        for j in range(Image.shape[1]):
            Captured_Color = Image[i, j, :].reshape([3])
            Color2 = np.dot(ColorMatrix, Captured_Color) + ColorConstant
            Color3 = 255.0 * np.power(Color2 / 255.0, ColorGamma)
            ImageCorrected[i, j, :] = np.uint8(Color3)
    return ImageCorrected

# Using modified Gamma Correction Algorithm by
# Constantinou2013 - A comparison of color correction algorithms for
# endoscopic cameras


def getColorMatchingErrorVectorised(Arg, Colors, Captured_Colors):
    ColorMatrix = Arg[:9].reshape([3, 3])
    ColorConstant = Arg[9:12].reshape([3, 1])
    ColorGamma = Arg[12:15]

    # We get warnings when base of power is negative. Ignore them as they
    # probably are not significant in the least square search
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        TempRGB = np.dot(ColorMatrix, Captured_Colors) + ColorConstant
        Corrected_Colors = np.zeros_like(TempRGB)
        Corrected_Colors[0, :] = 255.0*np.power(TempRGB[0, :]/255.0, ColorGamma[0])
        Corrected_Colors[1, :] = 255.0*np.power(TempRGB[1, :]/255.0, ColorGamma[1])
        Corrected_Colors[2, :] = 255.0*np.power(TempRGB[2, :]/255.0, ColorGamma[2])

    Diff = Colors - Corrected_Colors
    ErrorList = np.sqrt(np.sum(Diff * Diff, axis=0)).tolist()
    return ErrorList


def estimateColorParametersFromWhiteBackground(Image, Window, MaxIntensity=255):
    tlCnr = Window[0:2]
    brCnr = Window[2:]
    Captured_R = Image[tlCnr[1]:brCnr[1], tlCnr[0]:brCnr[0], 0].astype(np.float)
    Captured_G = Image[tlCnr[1]:brCnr[1], tlCnr[0]:brCnr[0], 1].astype(np.float)
    Captured_B = Image[tlCnr[1]:brCnr[1], tlCnr[0]:brCnr[0], 2].astype(np.float)
    Captured_R = np.median(Captured_R)
    Captured_G = np.median(Captured_G)
    Captured_B = np.median(Captured_B)
    scale_R = MaxIntensity / Captured_R
    scale_G = MaxIntensity / Captured_G
    scale_B = MaxIntensity / Captured_B
    colorMatrix = np.eye(3)
    colorConstant = np.zeros([3, 1])
    colorGamma = np.ones([3, 1])
    colorMatrix[0, 0] = scale_R
    colorMatrix[1, 1] = scale_G
    colorMatrix[2, 2] = scale_B
    return colorMatrix, colorConstant, colorGamma


def estimateColorParameters(TrueColors, ActualColors):
    # estimate color-correction parameters
    colorMatrix = np.eye(3)
    colorConstant = np.zeros([3, 1])
    colorGamma = np.ones([3, 1])
    Arg2 = np.zeros([9 + 3 + 3])
    Arg2[:9] = colorMatrix.reshape([9])
    Arg2[9:12] = colorConstant.reshape([3])
    Arg2[12:15] = colorGamma.reshape([3])
    ArgRefined, _ = optimize.leastsq(getColorMatchingErrorVectorised,
                                     Arg2, args=(TrueColors, ActualColors),
                                     maxfev=10000)
    colorMatrix = ArgRefined[:9].reshape([3, 3])
    colorConstant = ArgRefined[9:12].reshape([3, 1])
    colorGamma = ArgRefined[12:15]
    return colorMatrix, colorConstant, colorGamma


def correctColorVectorised(Image, ColorMatrix, ColorConstant, ColorGamma):
    Width, Height = Image.shape[1::-1]
    CapturedR = Image[:, :, 0].reshape([1, Width*Height])
    CapturedG = Image[:, :, 1].reshape([1, Width*Height])
    CapturedB = Image[:, :, 2].reshape([1, Width*Height])
    CapturedRGB = np.concatenate((CapturedR, CapturedG, CapturedB), axis=0)
    TempRGB = np.dot(ColorMatrix, CapturedRGB) + ColorConstant
    CorrectedRGB = np.zeros_like(TempRGB)
    CorrectedRGB[0, :] = 255.0*np.power(TempRGB[0, :]/255.0, ColorGamma[0])
    CorrectedRGB[1, :] = 255.0*np.power(TempRGB[1, :]/255.0, ColorGamma[1])
    CorrectedRGB[2, :] = 255.0*np.power(TempRGB[2, :]/255.0, ColorGamma[2])
    CorrectedR = CorrectedRGB[0, :].reshape([Height, Width])
    CorrectedG = CorrectedRGB[1, :].reshape([Height, Width])
    CorrectedB = CorrectedRGB[2, :].reshape([Height, Width])
    CorrectedR[np.where(CorrectedR < 0)] = 0
    CorrectedG[np.where(CorrectedG < 0)] = 0
    CorrectedB[np.where(CorrectedB < 0)] = 0
    CorrectedR[np.where(CorrectedR > 255)] = 255
    CorrectedG[np.where(CorrectedG > 255)] = 255
    CorrectedB[np.where(CorrectedB > 255)] = 255
    ImageCorrected = np.zeros_like(Image)
    ImageCorrected[:, :, 0] = CorrectedR
    ImageCorrected[:, :, 1] = CorrectedG
    ImageCorrected[:, :, 2] = CorrectedB
    return ImageCorrected


def rotateImage(Image, RotationAngle=0.0):
    if RotationAngle % 90.0 == 0:
        k = RotationAngle // 90.0
        Image_ = np.rot90(Image, k)
    elif RotationAngle != 0:
        center = tuple(np.array(Image.shape[1::-1]) / 2)
        rot_mat = cv2.getRotationMatrix2D(center, RotationAngle, 1.0)
        Image_ = cv2.warpAffine(Image, rot_mat, Image.shape[1::-1],
                                flags=cv2.INTER_LINEAR)
    return Image_


def matchTemplateLocation(Image, Template, EstimatedLocation,
                          SearchRange=[0.5, 0.5], RangeInImage=True):
    if RangeInImage:  # use image size
        Width = Image.shape[1]
        Height = Image.shape[0]
    else:  # use template size
        Width = Template.shape[1]
        Height = Template.shape[0]
    if SearchRange is None:  # search throughout the whole images
        CroppedHalfWidth = Width // 2
        CroppedHalfHeight = Height // 2
    elif SearchRange[0] <= 1.0 and SearchRange[1] <= 1.0:  # in fraction values
        CroppedHalfWidth = (Template.shape[1] + SearchRange[0] * Width) // 2
        CroppedHalfHeight = (Template.shape[0] + SearchRange[1] * Height) // 2
    else:  # in pixels values
        CroppedHalfWidth = (Template.shape[1] + SearchRange[0]) // 2
        CroppedHalfHeight = (Template.shape[0] + SearchRange[1]) // 2
    if CroppedHalfWidth > Image.shape[1] // 2 - 1:
        CroppedHalfWidth = Image.shape[1] // 2 - 1
    if CroppedHalfHeight > Image.shape[0] // 2 - 1:
        CroppedHalfHeight = Image.shape[0] // 2 - 1
    srchTLCnr = [max(EstimatedLocation[0]-CroppedHalfWidth, 0),
                 max(EstimatedLocation[1]-CroppedHalfHeight, 0)]
    srchBRCnr = [min(EstimatedLocation[0]+CroppedHalfWidth, Image.shape[1]),
                 min(EstimatedLocation[1]+CroppedHalfHeight, Image.shape[0])]
    return matchTemplateWindow(Image, Template, srchTLCnr, srchBRCnr)


def matchTemplateWindow(Image, Template, srchTLCnr, srchBRCnr):
    CropedImage = Image[srchTLCnr[1]:srchBRCnr[1], srchTLCnr[0]:srchBRCnr[0]]
    corrMap = cv2.matchTemplate(CropedImage.astype(np.uint8),
                                Template.astype(np.uint8),
                                cv2.TM_CCOEFF_NORMED)
    _, maxVal, _, maxLoc = cv2.minMaxLoc(corrMap)
    # recalculate max position in cropped image space
    matchedLocImageCropped = (maxLoc[0] + Template.shape[1] // 2,
                              maxLoc[1] + Template.shape[0] // 2)
    # recalculate max position in full image space
    matchedLocImage = (matchedLocImageCropped[0] + srchTLCnr[0],
                       matchedLocImageCropped[1] + srchTLCnr[1])
    return matchedLocImage, maxVal, maxLoc, corrMap


def createImagePyramid(Image, NoLevels=5):
    for i in range(NoLevels):
        if i == 0:
            PyramidImages = [Image.astype(np.uint8)]
        else:
            pyr_tmp = cv2.pyrDown(PyramidImages[i - 1])
            PyramidImages.append(pyr_tmp.astype(np.uint8))
    return PyramidImages


def matchTemplatePyramid(PyramidImages, PyramidTemplates, RotationAngle=None,
                         EstimatedLocation=None, SearchRange=None, NoLevels=4,
                         FinalLevel=1):
    for i in range(NoLevels - 1, -1, -1):
        if i == NoLevels - 1:
            if EstimatedLocation is None:
                maxLocEst = [PyramidImages[i].shape[1] // 2,
                             PyramidImages[i].shape[0] // 2]  # image center
            else:
                # scale position to the pyramid level
                maxLocEst = [EstimatedLocation[0] // 2 ** i,
                             EstimatedLocation[1] // 2 ** i]
            if SearchRange[0] > 1.0 and SearchRange[1] > 1.0:
                SearchRange2 = [SearchRange[0] // 2 ** i,
                                SearchRange[1] // 2 ** i]
            else:
                SearchRange2 = SearchRange
            matchedLocImage, maxVal, maxLoc, corrMap = \
                matchTemplateLocation(PyramidImages[i],
                                      PyramidTemplates[i],
                                      maxLocEst,
                                      SearchRange=SearchRange2)
            if RotationAngle is None:
                pyr_img_rot_uint8 = np.rot90(PyramidImages[i], 2).astype(np.uint8)
                matchedLocImage180, maxVal180, maxLoc180, corrMap180 = \
                    matchTemplateLocation(pyr_img_rot_uint8,
                                          PyramidTemplates[i],
                                          maxLocEst, SearchRange)
                if maxVal < 0.3 and maxVal180 < 0.3:
                    LOG.warn('Low matching score')
                if maxVal < maxVal180:
                    PyramidImages = [np.rot90(Img, 2) for Img in PyramidImages]
                    matchedLocImage, matchedLocImage180 = \
                        matchedLocImage180, matchedLocImage
                    maxVal, maxVal180 = maxVal180, maxVal
                    maxLoc, maxLoc180 = maxLoc180, maxLoc
                    corrMap, corrMap180 = corrMap180, corrMap
                    RotationAngle = 180
                else:
                    RotationAngle = 0
            # rescale to location in level-0 image
            matchedLocImage0 = (matchedLocImage[0] * 2 ** i,
                                matchedLocImage[1] * 2 ** i)
        else:
            maxLocEst = (matchedLocImage0[0] // 2 ** i,
                         matchedLocImage0[1] // 2 ** i)
            searchRange = [6, 6]
            matchedLocImage, maxVal, maxLoc, corrMap = \
                matchTemplateLocation(PyramidImages[i],
                                      PyramidTemplates[i],
                                      maxLocEst, searchRange)
            # rescale to location in level-0 image
            matchedLocImage0 = (matchedLocImage[0] * 2 ** i,
                                matchedLocImage[1] * 2 ** i)
        if i == FinalLevel:
            # Skip early to save time
            break
    return maxVal, matchedLocImage0, RotationAngle
