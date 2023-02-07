import re #To perform the search and replace.

try:
    from ..Script import Script
    runsStandalone = False
except:
    from typing import Optional, Any, Dict, TYPE_CHECKING, List
    import collections
    import json
    import sys

    class Script(object):
        def injectSettingData(self, jsonString):
            self._settingObj = json.loads(jsonString)

        def getSettingDataString(self):
            return "";

        def getSettingValueByKey(self, key: str) -> Any:
            try:
                return self._settingsObj[key]
            except:
                pass
            if not '_defaultSettingsObj' in dir(self):
                self._defaultSettingObj = json.loads(self.getSettingDataString())
            return self._defaultSettingObj["settings"][key]["default_value"]

    runsStandalone = True

class PenColorizer(Script):
    """Performs a search-and-replace on all g-code.
    Due to technical limitations, the search can't cross the border between
    layers.
    """

    def getSettingDataString(self):
        return """{
            "name": "PenColorizer",
            "key": "PenColorizer",
            "metadata": {},
            "version": 2,
            "settings":
            {
                "PenXOffset":
                {
                    "label": "Pen X Offset",
                    "description": "Offset of your pen in X direction",
                    "type": "float",
                    "default_value": 36.1
                },
                "PenYOffset":
                {
                    "label": "Pen Y Offset",
                    "description": "Offset of your pen in Y direction",
                    "type": "float",
                    "default_value": 45.8
                },
                "PenZOffset":
                {
                    "label": "Pen Z Offset",
                    "description": "Offset of your pen in Z direction",
                    "type": "float",
                    "default_value": 3.2
                },
                "FirstPenXPosition":
                {
                    "label": "First Pen X Position",
                    "description": "X position for holding the first pen in the pen rack",
                    "type": "float",
                    "default_value": 28.0
                },
                "FirstPenZPosition":
                {
                    "label": "First Pen Z Position",
                    "description": "Z position for holding the first pen in the pen rack",
                    "type": "float",
                    "default_value": 238.0
                },
                "ExtraRetraction":
                {
                    "label": "Retraction during painting",
                    "description": "Extra amount of retraction during painting",
                    "type": "float",
                    "default_value": 5.5
                },
                "Interlace":
                {
                    "label": "Interlace colors",
                    "description": "Only paint every second layer",
                    "type": "bool",
                    "default_value": true
                }
            }
        }"""

    def getPen(self, pen):    
        penside = pen % 2
        penoffset = float(int(pen / 2)) * 68.0
        
        if penside == 0:
            getlines = [";Get pen " + str(pen),
                        "G0 F5000 ; set speed fast",
                        "G0 X" + str(self.penstartx + penoffset) + " Z" + str(self.penstarty - 152.0) + " ;go under pen",
                        "G0 F2000 ; set speed slow",
                        "G0 X" + str(self.penstartx + penoffset) + " Z" + str(self.penstarty) + " ; lift pen",
                        "G0 X" + str(self.penstartx + 20.5 + penoffset) + " Z" + str(self.penstarty) + " ; move pen right",
                        "G0 F5000 ; set speed fast",
                        "G0 X" + str(self.penstartx + 20.5 + penoffset) + " Z" + str(self.penstarty - 152.0) + " ; lower pen"]
        else:
            getlines = [";Get pen " + str(pen),
                        "G0 F5000 ; set speed fast",
                        "G0 X" + str(self.penstartx + 41.0 + penoffset) + " Z" + str(self.penstarty - 152.0) + " ;go under pen",
                        "G0 F2000 ; set speed slow",
                        "G0 X" + str(self.penstartx + 41.0 + penoffset) + " Z" + str(self.penstarty) + " ; lift pen",
                        "G0 X" + str(self.penstartx + 20.5 + penoffset) + " Z" + str(self.penstarty) + " ; move pen right",
                        "G0 F5000 ; set speed fast",
                        "G0 X" + str(self.penstartx + 20.5 + penoffset) + " Z" + str(self.penstarty - 152.0) + " ; lower pen"]
        return getlines
        
    def putPen(self, pen):
        penside = pen % 2
        penoffset = float(int(pen / 2)) * 68.0
        
        if penside == 0:
            putlines = [";put pen " + str(pen),
                        "G0 F5000 ; set speed fast",
                        "G0 X" + str(self.penstartx + 20.5 + penoffset) + " Z" + str(self.penstarty - 152.0) + " ; go under pen",
                        "G0 X" + str(self.penstartx + 20.5 + penoffset) + " Z" + str(self.penstarty) + " ; lift pen",
                        "G0 F2000 ; set speed slow",
                        "G0 X" + str(self.penstartx + penoffset) + " Z" + str(self.penstarty) + " ; move pen left",
                        "G0 X" + str(self.penstartx + penoffset) + " Z" + str(self.penstarty - 152.0) + " ; lower pen",
                        "G0 F5000 ; set speed fast", ""]
        else:
            putlines = [";put pen " + str(pen),
                        "G0 F5000 ; set speed fast",
                        "G0 X" + str(self.penstartx + 20.5 + penoffset) + " Z" + str(self.penstarty - 152.0) + " ; go under pen",
                        "G0 X" + str(self.penstartx + 20.5 + penoffset) + " Z" + str(self.penstarty) + " ; lift pen",
                        "G0 F2000 ; set speed slow",
                        "G0 X" + str(self.penstartx + 41.0 + penoffset) + " Z" + str(self.penstarty) + " ; move pen left",
                        "G0 X" + str(self.penstartx + 41.0 + penoffset) + " Z" + str(self.penstarty - 152.0) + " ; lower pen",
                        "G0 F5000 ; set speed fast", ""]
        return putlines

    def offset(self, gcode, zoffset):
        coord = re.findall(r'[XYZF].?\d+(?:.\d+)?', gcode)
        newgcode = gcode[:2]
        
        F = next((i for i in coord if i.startswith('F')), None)
        if F != None:
            newgcode += " " + "F3600"#F
            
        X = next((i for i in coord if i.startswith('X')), None)
        if X != None:
            newgcode += " X" + "{:0.3f}".format((float(X[1:]) + self.xoffset))
            
        Y = next((i for i in coord if i.startswith('Y')), None)
        if Y != None:
            newgcode += " Y" + "{:0.3f}".format((float(Y[1:]) + self.yoffset))
            
        Z = next((i for i in coord if i.startswith('Z')), None)
        if Z != None:
            newgcode += " Z" + "{:0.3f}".format((float(Z[1:]) + self.zoffset + zoffset))
        
        return newgcode
        
    def lift(self, gcode, zoffset):
        coord = re.findall(r'[XYZF].?\d+(?:.\d+)?', gcode)
        newgcode = gcode[:2]
        
        F = next((i for i in coord if i.startswith('F')), None)
        if F != None:
            newgcode += " " + F
            
        X = next((i for i in coord if i.startswith('X')), None)
        if X != None:
            newgcode += " X" + "{:0.3f}".format((float(X[1:])))
            
        Y = next((i for i in coord if i.startswith('Y')), None)
        if Y != None:
            newgcode += " Y" + "{:0.3f}".format((float(Y[1:])))
            
        Z = next((i for i in coord if i.startswith('Z')), None)
        if Z != None:
            newgcode += " Z" + "{:0.3f}".format((float(Z[1:]) + zoffset))
        
        return newgcode
        
    def getFirstPos(self, lines):
        for line in lines:
            if "G0" in line or "G1" in line:
                coord = re.findall(r'[XYZ].?\d+(?:.\d+)?', line)
                
                X = next((i for i in coord if i.startswith('X')), None)
                Y = next((i for i in coord if i.startswith('Y')), None)
                Z = next((i for i in coord if i.startswith('Z')), None)
                
                if X != None and Y != None and Z != None:
                    return line
                
        return "; nothing found"
    
    def addExplicitZ(self, lines):
        newlines = []

        for line in lines:
            if "G0" in line or "G1" in line:
                newline = line
            
                coord = re.findall(r'[XYZF].?\d+(?:.\d+)?', line)
                Z = next((i for i in coord if i.startswith('Z')), None)
                if Z != None:
                    self.lastZ = float(Z[1:])
                else:
                    newline += " Z" + "{:0.3f}".format(self.lastZ)
                    
                newlines.append(newline)
            else:
                newlines.append(line)
                    
        return newlines
        
    def execute(self, data):
    
        self.penstartx = self.getSettingValueByKey("FirstPenXPosition")# 28.0
        self.penstarty = self.getSettingValueByKey("FirstPenZPosition")#238.0
    
        self.xoffset = self.getSettingValueByKey("PenXOffset")#36.1
        self.yoffset = self.getSettingValueByKey("PenYOffset")#45.3
        self.zoffset = self.getSettingValueByKey("PenZOffset")#3.2
        self.lastZ = 0.2
        layerheight = 0.2
        
        lastlayerx = 100.0
        lastlayery = 100.0
        lastlayerz = 0.3
        
        drawrectract = self.getSettingValueByKey("ExtraRetraction")
        interlace = self.getSettingValueByKey("Interlace")
        
        isRetractMove = True
    
        #iterate layers
        curT = 0
        for layer_number, layer in enumerate(data):
            lines = layer.split("\n")
            lines = self.addExplicitZ(lines)
            
            newlines = []
            isLayer = lines[0].startswith(";LAYER")
            
            #get pen & set height
            zheight = layerheight * (layer_number - 1)
            
            #setup drawbuffers
            drawlines = [None] * 8
            for i in range(8):
                drawlines[i] = ["; Draw Layer " + str(i)]
            
            isPrimeTower = False
            primelines = [";moved prime tower"]
            skirtlines = [";duplicated skirt lines"]

            isSkirt = False
            
            linestoskip = 0
            
            zhopOffset = 3.0
            
            wasG0move = False
            
            #iterate lines
            for line in lines:
                if linestoskip > 0:
                    linestoskip -= 1
                    continue
            
                if ";Layer height:" in line:
                    layerheight = float(line[14:])
                    newlines.append(line)
                #type change
                elif ";TYPE:" in line:
                    if ";TYPE:PRIME-TOWER" in line:
                        isPrimeTower = True
                        isSkirt = False
                    elif ";TYPE:SKIRT" in line or ";TYPE:SUPPORT" in line or ";TYPE:SUPPORT-INTERFACE" in line or ";TYPE:FILL" in line:
                        isSkirt = True
                        isPrimeTower = False
                    else:
                        isSkirt = False
                        isPrimeTower = False
                    
                    newlines.append(line)
            
                #offset G1 codes & remember curZ
                elif "G0" in line or "G1" in line:
                    coord = re.findall(r'[XYZEF].?\d+(?:.\d+)?', line)
                
                    #should we draw?
                    draw = curT >= 0 and isSkirt == False and isPrimeTower == False and ((layer_number + curT) % 2 == 0 or interlace == False)
                
                    #retract move?
                    E = next((i for i in coord if i.startswith('E')), None)
                    if E != None:
                        if float(E[1:]) < 0.0: 
                            isRetractMove = True
                            zhopOffset = 3.0 
                        else:
                            isRetractMove = False
                            zhopOffset = 0.0
                            
                    '''#G0 Move?
                    if "G0" in line:
                        zhopOffset = 3.0
                        
                        if wasG0move == False and draw == True: #we transition to G0 Move
                            drawlines[curT].append(self.offset(line, 0.0))
                    
                        wasG0move = True
                    else:
                        zhopOffset = 0.0 
                        
                        if wasG0move == True and draw == True: #we transition from G0 Move
                            drawlines[curT].append(self.offset(line, 3.0))
                        
                        wasG0move = False'''
                    
                
                    if  draw == True:
                        drawlines[curT].append(self.offset(line, zhopOffset))
                       
                    if isPrimeTower:
                        primelines.append(line)
                    else:
                        newlines.append(line)
                        
                    #remember last pos
                    
                    X = next((i for i in coord if i.startswith('X')), None)
                    if X != None:
                        lastlayerx = float(X[1:])
                        
                    Y = next((i for i in coord if i.startswith('Y')), None)
                    if Y != None:
                        lastlayery = float(Y[1:])
                        
                    Z = next((i for i in coord if i.startswith('Z')), None)
                    if Z != None:
                        lastlayerz = float(Z[1:])
                                            
                #filter out all dual extruder related gcodes but log which extruder should be active right now
                elif line.startswith("T"):
                    curT = int(line[1:]) - 1
                    newlines.append(";" + line)
                
                #filter out extruder related commands
                elif "T1" in line or "T2" in line or "T3" in line or "T4" in line or "T5" in line or "T6" in line or "T7" in line or "T8" in line:
                    newlines.append(";" + line)
                
                #filter out extruder heating commands
                elif "M109" in line and isLayer:
                     newlines.append(";" + line)
                elif "M104" in line and isLayer:
                     newlines.append(";" + line)
                elif "M105" in line and isLayer:
                     newlines.append(";" + line)
                    
                else:
                    newlines.append(line)

            #move prime tower to layer startswith
            #primelines.append(";end prime tower")
            #if len(primelines) > 3:
            #    newlines[2:2] = primelines
                
            #add drawlines
            if isLayer:# and layer_number % 2 == 0:
                newlines += ["G1 F1500 E-" + str(drawrectract)] #retract before drawing
                
                for i in range(8):
                    if len(drawlines[i]) <= 1:
                        continue
                        
                    drawlines[i][1:1] = [self.lift(self.getFirstPos(drawlines[i]), 3.0) + ";lower pen from above the first spot"] # lower pen from above the first spot
                    drawlines[i][1:1] = self.getPen(i)
                    drawlines[i] += [self.lift(drawlines[i][-1], 3.0) + "; raise pen from the last spot"] # raise pen from the last spot
                    drawlines[i] += self.putPen(i)

                    newlines += drawlines[i]
                
                #prime after drawing
                newlines += ["G0 X" + str(lastlayerx) + " Y" + str(lastlayery) + " Z" + str(lastlayerz + 2.0), 
                    "G0 X" + str(lastlayerx) + " Y" + str(lastlayery) + " Z" + str(lastlayerz) + " ;return to last pos after drawing"]
                newlines += ["G1 F1500 E" + str(drawrectract), ""]

            result = "\n".join(newlines)
            data[layer_number] = result

        return data

# run this if not executed via Cura
if runsStandalone == True:
    import argparse

    parser = argparse.ArgumentParser(description='Postprocess gcode file to add colors using pens.', exit_on_error=True)
    parser.add_argument('-c', '--config', help='path to the config json file', required=True)
    parser.add_argument('-i', '--input', help='path to the input gcode file', required=True)
    parser.add_argument('-o', '--output', help='path to the output gcode file', required=False)

    args = parser.parse_args()

    configFilename = args.config
    inputFilename = args.input
    outputFilename = args.output

    # create script instance
    script = PenColorizer()

    # read config
    hasConfig = False
    try:
        print("Reading config from " + configFilename);
        with open(configFilename, "r") as file:
            script.injectSettingData(file.read())
        hasConfig = True
    except FileNotFoundError:
        print("Config not found, falling back to defaults!")
    except BaseException as e:
        print("Error reading config: " + str(e))

    if hasConfig == False:
        print("### Defaults will most likely not work for your printer and can damage your machine! ###")
        input("Press Enter to continue anyway...")

    
    # read input gcode file
    print("Running script on " + inputFilename)
    with open(inputFilename) as file:
        lines = file.readlines()

    layersLineBuffers = []
    lineBuffer = []
    for i in range(0, len(lines)):
        line = lines[i]

        # check if a (virtual) layer starts here
        # virtual layers are the comment block at the beginning and the start gcode sequence
        isLayerStart = line.startswith(";LAYER:") or line.startswith(";Generated with")
        isLayerEnd = line.startswith(";TIME_ELAPSED")

        if isLayerStart or isLayerEnd:
            if isLayerEnd:
                lineBuffer.append(line)
            if len(lineBuffer) > 0:
                layersLineBuffers.append(lineBuffer.copy())
                lineBuffer.clear()

        if not isLayerEnd:
            lineBuffer.append(line)
    
    if len(lineBuffer) > 0:
        layersLineBuffers.append(lineBuffer.copy())

    # add comment stating this file was postprocessed
    layersLineBuffers[0].insert(len(layersLineBuffers[0]), ";POSTPROCESSED\n")

    # split fist line of last layer to its own layer so we conform with whatever cura does
    lastLayerLineBuffer = layersLineBuffers[len(layersLineBuffers)-1].copy();
    layersLineBuffers[len(layersLineBuffers)-1] = [lastLayerLineBuffer[0]]
    lastLayerLineBuffer.remove(lastLayerLineBuffer[0])
    layersLineBuffers.append(lastLayerLineBuffer)

    # merge layer lines to string
    layers = []
    for i in range(0, len(layersLineBuffers)):
        layers.append("".join(layersLineBuffers[i]))


    # execute script
    layers = script.execute(layers)


    # write output gcode file
    if outputFilename == None:
        outputFilename = inputFilename.partition(".gcode")[0] + ".processed.gcode"

    print("Writing processed file to " + outputFilename);
    with open(outputFilename, "w") as file:
        for i in range(0, len(layers)):
            file.write(layers[i])