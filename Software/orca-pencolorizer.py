#!/usr/bin/python
import sys
import re

###############################################################################################################################################################
# GLOBAL SCRIPT SETTING VARIABLES HERE - RESULTS FROM CALIBRATION
# PLEASE NOTE THIS SCRIPT WAS DESIGNED FOR RECTILINEAR KINEMATICS (CREALITY ENDER, PRUSA I, ETC). THIS SCRIPT WILL NOT WORK WITH COREXY KINEMATICS (BAMBU, ETC)
# ALSO NOTE THAT THE SCRIPT RELIES ON PROPERLY INSTALLED AND CALIBRATED PROJECT HARDWARE. DO NOT USE THIS SCRIPT WITHOUT APPROPRIATELY CALIBRATED HARDWARE
###############################################################################################################################################################
# Offset of your pen from the toolhead in X direction, values are added to the nozzle along the X axis and not relative.
penXOffset = 36
# Offset of your pen from the toolhead in Y direction, values are added to the nozzle along the Y axis and not relative.
penYOffset = 45
# Offset of your pen in Z direction, values are added to the nozzle along the Z axis and are relative FROM the pen TO the nozzle.
penZOffset = 3
# X coordinate for holding the first pen in the pen rack.
firstPenXPosition = 28
# Z coordinate for holding the first pen in the pen rack.
firstPenZPosition = 238
# Y cord for pen rack. Note theat this has to be where the pen holder can grab the pen.
penYposition = 330
# Extra amount of retraction during painting to avoid oozing.
extraRetraction = 5.5
# The number of unpainted layers to print between each painted layer. Larger numbers are useful for smaller layer heights.
interlace = 1
# Increase color depth by painting inner walls. Decreases print strength.
increaseColorDepth = False
# Color the entire mesh by painting everything except supports. Greatly decreases print strength. Overrides Increase Color Depth.
fullColorDepth = False

######################################################################
# Fallback coordinates to start painting when normal detection fails
# Global variables to preserve values between layers
######################################################################
fallbackX = 0.0
fallbackY = 0.0

def main(gCodeFile,gCodePath) -> None:
    layers = []
    try:
        gCodeLines = gCodeFile.readlines()
    except:
        print("Error processing input file")
        sys.exit()
        
    #outFile = open(str(os.getenv('SLIC3R_PP_OUTPUT_NAME')))
    try:
        outFile = open("test.gcode","w")
    except:
        print("Unable to open output file")
        sys.exit()

    layers = processLayers(gCodeLines)
    gCodeFile.close()
    for line in layers:
        outFile.write(f"{line}")
    outFile.close()
    
def processLayers(gcode:list) -> list:
    gCodeList = []
    buffer = []
    layerNumber = 0 # orca starts with a "layer" of print data
    for line in gcode:
        if ";LAYER_CHANGE" in line and not ";BEFORE_LAYER_CHANGE" in line:
            buffer = addLayerColors(buffer, layerNumber)
            gCodeList.extend(buffer)
            
            # start new layer
            layerNumber+= 1
            buffer = []
            buffer.append(";LAYER " + str(layerNumber) + " START\n")
            buffer.append(line)
        else:
            # continue building layer buffer
            buffer.append(line)

    # handle last layer
    buffer = addLayerColors(buffer,layerNumber)
    gCodeList.extend(buffer)

    return gCodeList

def addLayerColors(gCodeLayer:list, layer) -> list:
    #zero type blocks and set up drawbuffers
    isSkirt = False
    isSupport = False
    isFill = False
    isPrimeTower = False
    primelines = [";moved prime tower"]
    skirtlines = [";duplicated skirt lines"]
    isPaintBlock = False
    isPaintLayer = False
    drawlines = [[] for i in range(7)]
    paintStartX = [[] for i in range(7)]
    paintStartY = [[] for i in range(7)]
    currentT = -1
    currentZ = 0.000
    isToolSwitch = False
    newlines = []

    for line in gCodeLayer:
        # get the current layer height
        if getValue(line,"Z"):
              currentZ = float(getValue(line,"Z"))
        
        # switch on code block type and determine whether any paintable surface exists
        if ";TYPE" in line:
            
            # catch prime towers
            if "prime-tower" in line:
                isSkirt = False
                isSupport = False
                isFill = False
                isPrimeTower = True
                isPaintBlock = False
                isEndOfLayer = False

            # catch supports
            elif "support" in line:
                isSkirt = False
                isSupport = True
                isFill = False
                isPrimeTower = False
                isPaintBlock = False
                isEndOfLayer = False

            # catch skirts
            elif "support" in line:
                isSkirt = True
                isSupport = False
                isFill = False
                isPrimeTower = False
                isPaintBlock = False
                isEndOfLayer = False

            elif "Outer wall" in line:
                isSkirt = False
                isSupport = False
                isFill = False
                isPrimeTower = False
                isEndOfLayer = False

                # get the starting location for the virtual tool when printing with default values
                # this script presumes the order of of SUPPORT, *INFILL/*SURFACE, INNER WALL, OUTER WALL for gcode
                # outer walls are the second-last available paint block and only need the starting 2 if "Increase Color Depth" and "Full Color Depth" aren't selected
                # AND if there were no preceding inner walls or fill
                if currentT >= 0 and (isPaintBlock == False or isToolSwitch):
                     #look back for the most recent XY position
                    for i in range(-1, -6, -1):
                        try:
                            if getValue(newlines[i], "X") and getValue(newlines[i], "Y"):
                                paintStartX[currentT] = getValue(newlines[i], "X")
                                paintStartY[currentT] = getValue(newlines[i], "Y")
                                break
                        except IndexError:
                            paintStartX[currentT] = fallbackX
                            paintStartY[currentT] = fallbackY
                            break
                    
                    # reset tool flag
                    if isToolSwitch:
                        isToolSwitch = False

                # outer walls are always painted
                isPaintBlock = True

            elif "Inner wall" in line:
                isSkirt = False
                isSupport = False
                isFill = False
                isPrimeTower = False
                isEndOfLayer = False

                #get the starting location for the virtual tool when "Increase Color Depth" is selected
                #this is the second paint block if "Full Color Depth" is selected and is not the starting 2 AND there was no preceding infill
                if currentT >= 0 and (increaseColorDepth or fullColorDepth) and (isPaintBlock == False or isToolSwitch):
                    #look back for the most recent XY 2
                    for i in range(-1, -6, -1):
                        try:
                            if getValue(newlines[i], "X") and getValue(newlines[i], "Y"):
                                paintStartX[currentT] = getValue(newlines[i], "X")
                                paintStartY[currentT] = getValue(newlines[i], "Y")
                                break
                        except IndexError:
                            paintStartX[currentT] = fallbackX
                            paintStartY[currentT] = fallbackY
                            break
                    
                    # reset tool flag
                    if isToolSwitch:
                        isToolSwitch = False

                # mark block for painting if "Increase Color Depth" or "Full Color Depth" are selected
                if currentT >= 0 and (increaseColorDepth or fullColorDepth):
                    isPaintBlock = True
                else:
                    isPaintBlock = False

            elif "infill" in line:
                isSkirt = False
                isSupport = False
                isFill = False
                isPrimeTower = False
                isEndOfLayer = False

                #get the starting location for the virtual tool when "Full Color Depth" is selected
                #if selected, this will be the starting 2 for painting unless there is an exterior surface block
                if currentT >= 0 and fullColorDepth and isToolSwitch:
                    #look back for the most recent XY 2
                    for i in range(-1, -6, -1):
                        try:
                            if getValue(newlines[i], "X") and getValue(newlines[i], "Y"):
                                paintStartX[currentT] = getValue(newlines[i], "X")
                                paintStartY[currentT] = getValue(newlines[i], "Y")
                                break
                        except IndexError:
                            paintStartX[currentT] = fallbackX
                            paintStartY[currentT] = fallbackY
                            break
                    
                    # reset tool flag
                    if isToolSwitch:
                        isToolSwitch = False

                # mark block for painting if "Increase Color Depth" or "Full Color Depth" are selected
                if currentT >= 0 and (fullColorDepth):
                    isPaintBlock = True
                else:
                    isPaintBlock = False

            elif "surface" in line:
                isSkirt = False
                isSupport = False
                isFill = False
                isPrimeTower = False
                isEndOfLayer = False

                # surfaces are the first paintable block and will always be the starting position for the virtual tool when present
                if currentT >= 0 and isToolSwitch:
                    #look back for the most recent XY position
                    for i in range(-1, -6, -1):
                        try:
                            if getValue(newlines[i], "X") and getValue(newlines[i], "Y"):
                                paintStartX[currentT] = getValue(newlines[i], "X")
                                paintStartY[currentT] = getValue(newlines[i], "Y")
                                break
                        except IndexError:
                            paintStartX[currentT] = fallbackX
                            paintStartY[currentT] = fallbackY
                            break
                    
                        # reset tool flag
                        if isToolSwitch:
                            isToolSwitch = False

                    # surfaces are always painted
                    isPaintBlock = True
            
            # paint flags are set, pass the line itself to the buffer
            newlines.append(line)

        #Handle G0/G1 commands and copy drawlines and draw start positions to buffer
        elif "G0" in line or "G1" in line:
        #should we draw?
            if currentT >= 0 and isPaintBlock and (layer % (interlace + 1) == 0):
                drawlines[currentT].append(offset(line, currentZ) + "\n")
                isPaintLayer = True

            if isPrimeTower:
                primelines.append(line)
            else:
                newlines.append(line)

        #filter extruder commands, log the active extruder
        elif str(line).startswith("T"):
            if getValue(line, "T") and int(getValue(line, "T") - 1) != currentT:
                isToolSwitch = True

            currentT = int(getValue(line, "T") - 1)
            newlines.append(";" + line)

        #filter out extruder related commands
        elif "T1" in line or "T2" in line or "T3" in line or "T4" in line or "T5" in line or "T6" in line or "T7" in line or "T8" in line:
            newlines.append(";" + line)

        #filter out extruder heating commands
        elif "M109" in line:
            pass
        elif "M104" in line:
            pass
        elif "M105" in line:
            pass

        #filter extruder commands
        elif getValue(line, "T"):
            newlines.append(";" + line)

        # pass through all other gcode
        else:
            newlines.append(line)

    if isPaintLayer:
        # process paint blocks for the layer if there is anything to paint
        # retract extruder before painting
        newlines.append("G1 F4000 E-" + str(extraRetraction) + "\n")

        for i in range(7):
            # check for data (not just header) in each buffer
            if not drawlines[i]:
                continue

            else:
                # get pen, move pen into position, draw lines, disengage pen, return pen
                newlines.extend(getPen(i))
                newlines.append(offset("G0 X" + str(paintStartX[i]) + " Y" + str(paintStartY[i]), currentZ + 3.0) + "\n")
                newlines.append(offset("G0 X" + str(paintStartX[i]) + " Y" + str(paintStartY[i]), currentZ) + "\n")
                newlines.extend(drawlines[i])
                newlines.append(offset("G0", currentZ + 3.0) + "\n")
                newlines.extend(returnPen(i))

        # prime extruder after painting
        newlines.append("G1 F4000 E" + str(extraRetraction) + "\n")

    # get fallback values in case of malformed gcode
    if getValue(line,"X") and getValue(line,"Y"):
            fallbackX = getValue(line,"X")
            fallbackY = getValue(line,"Y")
    return newlines

def offset(gcode, currentZ):
    newgcode = "G0"

    # treat paint commands by offsetting and changing speed. Z is static for each layer
    if getValue(gcode, "F"):
        newgcode += " F3600"

    if getValue(gcode, "X"):
        newgcode += " X" + str(getValue(gcode, "X") + penXOffset)

    if getValue(gcode, "Y"):
        newgcode += " Y" + str(getValue(gcode, "Y") + penYOffset)

    newgcode += " Z" + str(currentZ + penZOffset)
        
    return newgcode

def getPen(pen):
    penside = pen % 2
    penoffset = float(int(pen / 2)) * 68.0
        
    # generate gcode to fetch the appropriate pen
    if penside == 0:
        getlines = ["; Get pen " + str(pen) + "\n",
                    "G0 F7000 Y" + str(penYposition) + " ; move Y axis to under pen rack",
                    "G0 F7000 X" + str(firstPenXPosition + penoffset) + " Z" + str(firstPenZPosition - 152.0) + " ; go under pen\n",
                    "G0 F2000 ; set speed slow\n",
                    "G0 Z" + str(firstPenZPosition) + " ; lift pen\n",
                    "G0 X" + str(firstPenXPosition + 20.5 + penoffset) + " ; move pen right\n",
                    "G0 F7000 ; set speed fast\n",
                    "G0 X" + str(firstPenXPosition + 20.5 + penoffset) + " Z" + str(firstPenZPosition - 152.0) + " ; lower pen\n"]
        
    else:
        getlines = ["; Get pen " + str(pen) + "\n",
                    "G0 F7000 Y" + str(penYposition) + " ; move Y axis to under pen rack",
                    "G0 F7000 X" + str(firstPenXPosition + 41 + penoffset) + " Z" + str(firstPenZPosition - 152.0) + " ; go under pen\n",
                    "G0 F2000 ; set speed slow\n",
                    "G0 Z" + str(firstPenZPosition) + " ; lift pen\n",
                    "G0 X" + str(firstPenXPosition + 20.5 + penoffset) + " ; move pen left\n",
                    "G0 F7000 ; set speed fast\n",
                    "G0 X" + str(firstPenXPosition + 20.5 + penoffset) + " Z" + str(firstPenZPosition - 152.0) + " ; lower pen\n"]
            
    return getlines

def returnPen(pen):
    penside = pen % 2
    penoffset = float(int(pen / 2)) * 68

    # generate gcode to replace the appropriate pen
    if penside == 0:
        placelines = ["; Replace pen " + str(pen) + "\n",
                    "G0 F7000 ; set speed fast\n",
                    "G0 F7000 Y" + str(penYposition) + " ; move Y axis to under pen rack",
                    "G0 X" + str(firstPenXPosition + 20.5 + penoffset) + " Z" + str(firstPenZPosition - 152) + " ; go under gap\n",
                    "G0 Z" + str(firstPenZPosition) + " ; lift pen\n",
                    "G0 F2000 ; set speed slow\n",
                    "G0 X" + str(firstPenXPosition + penoffset) + " ; move pen left\n",
                    "G0 Z" + str(firstPenZPosition - 152) + " ; lower pen\n",
                    "G0 F7000 ; set speed fast\n"]
            
    else:
        placelines = ["; Replace pen " + str(pen) + "\n",
                    "G0 F7000 ; set speed fast\n",
                    "G0 F7000 Y" + str(penYposition) + " ; move Y axis to under pen rack",
                    "G0 X" + str(firstPenXPosition + 20.5 + penoffset) + " Z" + str(firstPenZPosition - 152) + " ; go under gap\n",
                    "G0 Z" + str(firstPenZPosition) + " ; lift pen\n",
                    "G0 F2000 ; set speed slow\n",
                    "G0 X" + str(firstPenXPosition + 41.0 + penoffset) + " ; move pen left\n",
                    "G0 Z" + str(firstPenZPosition - 152) + " ; lower pen\n",
                    "G0 F7000 ; set speed fast\n"]
            
    return placelines

def getValue(line, key, default = None) -> any:
    if not key in line or (';' in line and line.find(key) > line.find(';')):
        return default
    subPart = line[line.find(key) + 1:]
    m = re.search('^-?[0-9]+\.?[0-9]*', subPart)
    if m is None:
        return default
    try:
        return float(m.group(0))
    except:
        return default
    return default

def getFileStreamAndPath(read=True):
    # if len(sys.argv) != 2:
    # print("Usage: python3 ex1.py <filename>")
    # sys.exit(1)
    # filepath = sys.argv[1]
    filepath = "/home/mkurtz/OrcaCube_DualTest.gcode"
    try:
        if read:
            f = open(filepath, "r")
        else:
            f=open(filepath, "w")    
        return f,filepath
    except IOError:
        print("File not found")
        input("File not found.Press enter.")
        sys.exit(1)

if __name__ == "__main__":
    gCodeFile,gCodePath = getFileStreamAndPath()
    main(gCodeFile,gCodePath)
