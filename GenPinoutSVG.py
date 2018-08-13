#!/usr/bin/env python3
"""ESP32-MAXIO Pinout SVG Generator

Usage:
  GenPinoutSVG.py <filename.csv> [--overwrite]
  GenPinoutSVG.py <filename.csv> <filename.svg> [--overwrite]
  GenPinoutSVG.py (-h | --help)
  GenPinoutSVG.py --version

Options:
  -h --help     Show this screen.
  --version     Show version.

  Copyright (C) 2018  Steven Johnson
  This program comes with ABSOLUTELY NO WARRANTY; 
  This is free software, and you are welcome to redistribute it
  under the conditions of the GPL-3 License.
"""
VERSION='Generator Pinout Datasheets in SVG format - 1.0'

from docopt import docopt
from pathlib import Path
import csv
import svgwrite
from wand.image import Image
import base64
from pprint import pprint
import urllib.request
import math


################################################## GLOBAL VARIABLES ########################################
pagedimensions = {
  'A4-P' : (210, 297), # mm (portrait)
  'A4-L' : (297, 210), # mm (landscape)
  'A3-P' : (297, 420), # mm (portrait)
  'A3-L' : (420, 297)  # mm (landscape)
}

FixedThemeEntries = ["DEFAULT", "TYPE", "GROUP"]

svg_filename = None
dwg = None

mode = "SETUP"       # Start in Setup Mode (Reading Setup Commands)
pagetype='A4-L'      # Page Size
pagedpi=300          # Page DPI
pin_func_types=None  # Pin function types (Columns for Pin Description)

themes={}            # Configured themes
linesettings={}      # Line settings
messagesettings={    # Text message settings
  "X" : 0,
  "Y" : 0,
  "OffsetX" : 0,
  "OffsetY" : 0,
  "LineStep" : 0,
  "Font"     : "",
  "FontSize" : 0,
  "XJustify" : "center",
  "YJustify" : "center",
  "SVGText"  : None,
}

AnchorX = 0
AnchorY = 0
OffsetX = 0
OffsetY = 0

def EmptyRow(row):
  for x in row:
    if x != "":
      return False
  return True

def GetPageDimensions(pagetype=pagetype, dpi=pagedpi):
  if (pagetype not in pagedimensions):
    print("ERROR: Unkown Page Type {}. Defaulting to 'A4-L'".format(pagetype))
    pagetype = "A4-L"

  pagesize = (pagedimensions[pagetype][0], pagedimensions[pagetype][1])
  pageresolution = ((int(round((pagedimensions[pagetype][0] * dpi) / 25.4))),
                    (int(round((pagedimensions[pagetype][1] * dpi) / 25.4))))

  return ( pagesize, pageresolution)

def param_to_int(param, index, default=None):
  try: 
    return int(param[index])
  except (ValueError, IndexError):
    return default

def param_to_float(param, index, default=None):
  try: 
    return float(param[index])
  except (ValueError, IndexError):
    return default

def param_to_size(param, index, default=None):    
  # A Size is either an integer, or a percentage
  # A percentage is encoded as a real number between 0.0000 and 0.9999
  # 0.9999 = 100%
  try: 
    val = param[index]
    if (val.endswith('%')):
      val = val[:-1] # strip percent
      val = int(val)
      val = (0.9999 * min(val,100)) / 100
      return val
    else:
      return(int(val))
  except (IndexError, ValueError):
    return default

def get_size(size, max_size, default=None):
  if size is None:
    if default is None:
      return max_size
    else:
      return default

  if size >=1:
    return size
  else:
    return ((size / 0.9999) * max_size)     # Correct percentage to be 0-100%

def param_to_str(param, index, default=None):
  try: 
    if len(param[index]) == 0:
      return default
    return param[index]
  except IndexError:
    return default

def writeImage(params):
  """
      IMAGE, name, X, Y, W, H, <cx>, <cy>, <cw>, <ch>, <rot> 
      - Puts a PNG on the page at the requested location and for the requested size, with an optional crop and rotate.
  """
  global dwg

  imgfile = Path(params[1])
  X   = param_to_size(params, 2,0)     # Center of Image Location
  Y   = param_to_size(params, 3,0)     # Center of Image Location
  W   = param_to_size(params, 4,None)  # Size
  H   = param_to_size(params, 5,None)  # Size
  cx  = param_to_int(params, 6,None)   # Optional Crop Location (Relative to original image)
  cy  = param_to_int(params, 7,None)   # Optional Crop Location (Relative to original image)
  cw  = param_to_int(params, 8,None)   # Optional Crop Size (Relative to original image)
  ch  = param_to_int(params, 9,None)   # Optional Crop Size (Relative to original image)
  rot = param_to_int(params, 10,0)      # Get Rotation, default to no rotation

  if not imgfile.is_file():
    print("ERROR: Image {} Not Found!".format(str(imgfile.resolve())))
    return False

  with Image(filename=str(imgfile)) as img:
    # Crop
    if (cx is not None) and (cy is not None) and (cw is not None) and (ch is not None):
      img.crop(left=cx, right=cy, width=cw, height=ch)
    elif (cx is not None) or (cy is not None) or (cw is not None) or (ch is not None):
      print("ERROR: Crop Parameter Missing, <cx>, <cy>, <cw>, <ch> must all be specified, or NONE!")
      return False

    # Resize
    if (W is not None) or (H is not None):
      W = round(get_size(W,img.width))
      H = round(get_size(H,img.height))
      img.resize(width=W, height=H)

    # Rotate
    img.rotate(rot)

    # Then get raw PNG data and encode DIRECTLY into the SVG file.
    image_data = img.make_blob(format='png')
    encoded = base64.b64encode(image_data).decode()
    pngdata = 'data:image/png;base64,{}'.format(encoded)

    pagedimensions = GetPageDimensions()

    X = get_size(X, pagedimensions[1][0], 0)
    Y = get_size(Y, pagedimensions[1][1], 0)

    # Correct for Center
    X = X - (img.width/2)
    Y = Y - (img.height/2)

    image = dwg.add(dwg.image(href=(pngdata), insert=(X,Y)))
  return True

def writeIcon(params):
  """
      ICON, name.svg, X,Y,W,H,<rot>                 
      - Embeds another SVG inside this one. (Used for icons)
  """
  global dwg

  imgfile = Path(params[1])
  X   = param_to_size(params,2,0)     # Image Center
  Y   = param_to_size(params,3,0)     # Image Center
  W   = param_to_size(params,4,None)  # Size
  H   = param_to_size(params,5,None)  # Size
  rot = param_to_int(params,6,0) # Get Rotation, default to no rotation

  if not imgfile.is_file():
    print("ERROR: Image {} Not Found!".format(str(imgfile.resolve())))
    return False

  with Image(filename=str(imgfile)) as img:
    if (img.format != 'SVG'):
      print("ERROR: Icon Image MUST be an SVG!")
      return False

    # Then get raw PNG data and encode DIRECTLY into the SVG file.
    image_data = img.make_blob()
    encoded = base64.b64encode(image_data).decode()
    pngdata = 'data:image/svg+xml;base64,{}'.format(encoded)

    W = round(get_size(W,img.width))
    H = round(get_size(H,img.height))

    pagedimensions = GetPageDimensions()

    X = get_size(X, pagedimensions[1][0], 0)
    Y = get_size(Y, pagedimensions[1][1], 0)

    # Correct for Center
    X = X - (img.width/2)
    Y = Y - (img.height/2)

    icon = dwg.image(href=(pngdata), insert=(X,Y), size=(W,H))
    icon.rotate(rot)

    image = dwg.add(icon)
  return True
  
def GetTheme(theme, element, default=None):
  global themes
  element = element.upper()
  try:
    result = themes[theme][element]
    if ((result != "") and (result is not None)):
      return result
  except KeyError:
    pass
  
  try:
    return themes["DEFAULT"][element]
  except:
    return default

# Creates colored blocks and text for fields
def TextBox(X, Y, theme, contents, justX="CENTER", justY="CENTER", W=None, H=None):
    global dwg
    global themes

    border_color = GetTheme(theme,"Border Color",'red')
    border_width = GetTheme(theme,"Border Width",1)
    border_opacity = GetTheme(theme,"Border Opacity",1)
    fill_color   = GetTheme(theme,"Fill Color",'blue')
    opacity      = GetTheme(theme,"Opacity",50)
    font         = GetTheme(theme,"Font",'sans-serif')
    fontsize     = GetTheme(theme,"Font Size",10)
    fontcolor    = GetTheme(theme,"Font Color",'yellow')
    fontslant    = GetTheme(theme,"Font Slant","normal")
    fontbold     = GetTheme(theme,"Font Bold","normal")
    fontstretch  = GetTheme(theme,"Font Stretch","normal")

    boxname      = GetTheme(theme,"BOXES")
    if (boxname is None):
      boxtheme = theme
    else:
      boxtheme = "BOX_"+boxname

    if boxtheme in themes:
      boxtheme = "BOX_"+boxname
    else:
      print("ERROR: BOX Theme {} not known!".format(boxtheme))
      return False

    if (W is None):
      W            = GetTheme(boxtheme,"Width", 0)
    if (H is None):
      H            = GetTheme(boxtheme,"Height", 0)
    corner_rx    = GetTheme(boxtheme,"Corner RX", 0)
    corner_ry    = GetTheme(boxtheme,"Corner RY", 0)
    skew         = GetTheme(boxtheme,"Skew",0)

    if (justX == "LEFT"):
      xanchor = 'start'
      xalign = -(W/2)
    elif (justX == "RIGHT"):
      xanchor = 'end'
      xalign = (W/2)
    else:
      xanchor = 'middle'
      xalign = 0

    if (justY == "TOP"):
      yalign = -(H/2)+(fontsize)
    elif (justY == "BOTTOM"):
      yalign = (H/2)-(fontsize/2)
    else:
      yalign = 0+(fontsize/3)

    boxgroup = dwg.g()

    # Box
    rect = boxgroup.add(dwg.rect(
        ((0-W)/2, (0-H)/2), (W, H), corner_rx, corner_ry,
        stroke = border_color, fill_opacity = opacity, fill = fill_color,
        stroke_width = border_width, stroke_opacity = border_opacity
        ))
    if (skew != 0):
      rect.skewX(skew)

    # Text
    if ((contents is not None) and (contents != "")):
      boxgroup.add(dwg.text(
          contents,
          (xalign, yalign),
          font_size = fontsize, font_family=font, fill = fontcolor,
          font_style = fontslant,
          font_weight = fontbold,
          font_stretch = fontstretch,
          text_anchor=xanchor))               

    boxgroup.translate(X+(W/2),Y+(H/2))

    dwg.add(boxgroup)


def SetupDraw(row):
  global dwg
  global mode

  checkBoxes()

  pagedimensions = GetPageDimensions()
  size = (str(pagedimensions[0][0])+"mm", str(pagedimensions[0][1])+"mm")
  pixels = ("0 0 {} {}".format(pagedimensions[1][0], pagedimensions[1][1]))

  dwg = svgwrite.Drawing(
    str(svg_filename), 
    profile='full', 
    size=size,
    viewBox=pixels)
  mode = "DRAW"
  return True

def SetLabels(row):
  global pin_func_types
  global themes

  if pin_func_types is None:
    if len(row) > (len(FixedThemeEntries)+1):

      i = 0
      same = True
      while (i < len(FixedThemeEntries)):
        if row[i+1] != FixedThemeEntries[i]:
          same = False
          break
        i += 1

      if same:
        pin_func_types = row[(len(FixedThemeEntries)+1):]

        # Populate Empty theme dictionary
        for label in row[1:]:
          themes[label] = {}

      else:
        print("Error: First labels must be {}!".format(FixedThemeEntries))  
        return False
    else:
      print("Error: Not enough parameters to LABEL, Needs at least {}, <pin> !".format(FixedThemeEntries))  
      return False
    
  else:
    print("Error: Can only set the pin function labels ONCE!")
    return False
  return True

def SetTheme(row,pfunc):
  global themes

  theme_entry = row[0]
  i = 0
  for label in FixedThemeEntries + pin_func_types:
    value = pfunc(row,i+1)
    if ((i == 0) and (value == None)):
      print("ERROR: DEFAULT Entry can not be blank, must be set.")
      return False
    themes[label][theme_entry] = value
    i = i+1
  return True

def SetThemeInt(row):
  return SetTheme(row,param_to_int)

def SetThemeFloat(row):
  return SetTheme(row,param_to_float)

def SetThemeStr(row):
  return SetTheme(row,param_to_str)

def SetPageSize(row):
  global pagetype
  global pagedimensions

  page = param_to_str(row,1)

  if page in pagedimensions:
    pagetype = page
  else:
    print("ERROR: Unknown Page Type. Valid pages = {}?".format(list(pagedimensions.keys())))
    return False
  return True

def SetDPI(row):
  global pagedpi

  dpi = param_to_int(row,1)

  if ((dpi >= 50) and (dpi <= 1200)):
    pagedpi = dpi
  else:
    print("ERROR: DPI out of range, must be between 50 and 1200, Inclusive!")
    return False
  return True

PINWIRES = [
  "DIGITAL",
  "PWM",
  "ANALOG",
  "POWER"
]

PINTYPES = [
  "IO",
  "INPUT",
  "OUTPUT",
]

def SetPinType(row):
  global themes

  if (row[1] in PINTYPES):
    themeentry = "PINTYPE_"+row[1]
    color   = param_to_str(row, 2)
    opacity = param_to_float(row, 3)
    themes[themeentry] = { }

    if (color is not None):
      themes[themeentry]["FILL COLOR"] = color
    if (opacity is not None):
      themes[themeentry]["OPACITY"] = opacity
  else:
    print ("ERROR: <pintype> must be one of {}".format(PINTYPES))
    return False
  return True

def SetWireType(row):
  global themes

  if (row[1] in PINWIRES):
    themeentry = "PINWIRE_"+row[1]
    color   = param_to_str(row, 2)
    opacity = param_to_float(row, 3)
    thickness = param_to_int(row, 4)

    themes[themeentry] = { }

    if (color is not None):
      themes[themeentry]["FILL COLOR"] = color
    if (opacity is not None):
      themes[themeentry]["OPACITY"] = opacity
    if (thickness is not None):
      themes[themeentry]["THICKNESS"] = opacity
  else:
    print ("ERROR: <wiretype> must be one of {}".format(PINWIRES))
    return False
  return True

def SetPinGroup(row):
  global themes

  themeentry = "GROUP_"+row[1]
  color   = param_to_str(row, 2)
  opacity = param_to_float(row, 3)
  themes[themeentry] = { }

  if (color is not None):
    themes[themeentry]["FILL COLOR"] = color
  if (opacity is not None):
    themes[themeentry]["OPACITY"] = opacity

  return True

def DefineBox(params):
  global themes
  boxname = param_to_str(params,1)
  if (boxname is None):
    print("Error: Must specify box name")
    return False
  themeentry = "BOX_"+boxname
  themes[themeentry] = {}
  themes[themeentry]["BORDER COLOR"] = param_to_str(params,2)
  themes[themeentry]["BORDER OPACITY"] = param_to_float(params,3)
  themes[themeentry]["FILL COLOR"] = param_to_str(params,4)
  themes[themeentry]["OPACITY"] = param_to_float(params,5)
  themes[themeentry]["BORDER WIDTH"] = param_to_int(params,6)
  themes[themeentry]["WIDTH"]       = param_to_int(params,7)
  themes[themeentry]["HEIGHT"]      = param_to_int(params,8)
  themes[themeentry]["CORNER RX"]   = param_to_int(params,9)
  themes[themeentry]["CORNER RY"]   = param_to_int(params,10)
  themes[themeentry]["SKEW"]        = param_to_int(params,11)

  return True

def checkBoxes():
  global themes
  for theme in themes:
    if "BOXES" in themes[theme]:
      if ((themes[theme]["BOXES"] is not None) and ("BOX_"+themes[theme]["BOXES"] not in themes)):
        print ("ERROR: Box {} Used for {} Theme, but not defined!".format(themes[theme]["BOXES"], theme))


def moveAnchor(params):
  global AnchorX
  global AnchorY
  global OffsetX
  global OffsetY

  X = param_to_size(params,1)
  Y = param_to_size(params,2)

  if ((X is None) or (Y is None)):
    print("ERROR: Both X and Y must be defined!")
    return False

  AnchorX = X
  AnchorY = Y
  OffsetX = 0
  OffsetY = 0

  return True

VALIDSIDES = [ "LEFT","RIGHT","TOP LEFT","TOP RIGHT","BOTTOM LEFT","BOTTOM RIGHT" ]
VALIDPACKING = [ "PACKED","UNPACKED" ]
VALIDJUSTIFYX = ["LEFT", "CENTER", "RIGHT"]
VALIDJUSTIFYY = ["TOP", "CENTER", "BOTTOM"]

def StartPinSet(params):
  global linesettings

  valid = True
  #  PINSET <Side>, <Pack>, <Justify>, <LineStep>, <LeaderOffset>, <Column Gap>, <LeaderHStep>
  side = param_to_str(params,1,"LEFT").upper()
  packing = param_to_str(params,2,"UNPACKED").upper()
  justifyX = param_to_str(params,3,"CENTER").upper()
  justifyY = param_to_str(params,4,"CENTER").upper()
  linestep = param_to_int(params,5,10)
  leader   = param_to_int(params,6,10)
  gap      = param_to_int(params,7,10)
  hstep    = param_to_int(params,8,0)

  if side not in VALIDSIDES:
    print("ERROR: <Side> must be one of {}".format(VALIDSIDES))
    valid = False

  if packing not in VALIDPACKING:
    print("ERROR: <Pack> must be one of {}".format(VALIDPACKING))
    valid = False

  if justifyX not in VALIDJUSTIFYX:
    print("ERROR: <Justify X> must be one of {}".format(VALIDJUSTIFYX))
    valid = False

  if justifyY not in VALIDJUSTIFYY:
    print("ERROR: <Justify Y> must be one of {}".format(VALIDJUSTIFYY))
    valid = False

  if valid:   
    linesettings = {}
    linesettings["SIDE"]     = side
    linesettings["PACK"]     = (packing == "PACKED")
    linesettings["JUSTIFY X"]  = justifyX
    linesettings["JUSTIFY Y"]  = justifyY
    linesettings["LINESTEP"] = linestep
    linesettings["LEADER"]   = leader
    linesettings["GAP"]      = gap
    linesettings["hstep"]    = hstep

  return valid

def writePins(params):
  def incOffsetX(X,side,theme):
    boxtheme = "BOX_"+GetTheme(theme,"Boxes","STD")
    if ((side == "LEFT") or (side == "TOP LEFT") or (side == "BOTTOM LEFT")):
      X = X - (linesettings["GAP"] + GetTheme(boxtheme,"Width",0))
    elif ((side == "RIGHT") or (side == "TOP RIGHT") or (side == "BOTTOM RIGHT")):
      X = X + (linesettings["GAP"] + GetTheme(boxtheme,"Width",0))
    return X
  global OffsetX
  global OffsetY
  global AnchorX
  global AnchorY

  ok = True

  # PIN, <Icon>, <TYPE>, <GROUP>, <List of Pin attribute strings>   - Pin Attributes to print at next pin line.

  if linesettings == {}:
    print("Error: Line not setup with prior PINSET!")
    return False

  wire = param_to_str(params,1)
  pintype = param_to_str(params,2)
  pingroup = param_to_str(params,3)

  # printPin - Draw the Pin Icon and Leader line

  BoxOffsetX = 0

  for index, item in enumerate(params[4:]):
    if (index < len(pin_func_types)):
      pinfunc = param_to_str(params,index+4)
      theme = pin_func_types[index]

      if (pinfunc is not None):
        TextBox(AnchorX+OffsetX+BoxOffsetX,AnchorY+OffsetY, theme, pinfunc,    linesettings["JUSTIFY X"], linesettings["JUSTIFY Y"])
        BoxOffsetX = incOffsetX(BoxOffsetX,linesettings["SIDE"],theme)
      elif (not linesettings["PACK"]):
        BoxOffsetX = incOffsetX(BoxOffsetX,linesettings["SIDE"],theme)
    else:
      print("WARNING: Too many entries on line, extra entries discarded!")        
      ok = False
      break

  OffsetY += linesettings["LINESTEP"]
  return ok

def writePinText(params):
  global OffsetX
  global OffsetY
  global AnchorX
  global AnchorY

  ok = True

  if linesettings == {}:
    print("Error: Line not setup with prior PINSET!")
    return False

  wire = param_to_str(params,1)
  pintype = param_to_str(params,2)
  pingroup = param_to_str(params,3)
  theme = param_to_str(params,4)
  message = param_to_str(params,5)

  font         = GetTheme(theme,"Font",'sans-serif')
  fontsize     = GetTheme(theme,"Font Size",10)
  fontcolor    = GetTheme(theme,"Font Color",'yellow')
  fontslant    = GetTheme(theme,"Font Slant","normal")
  fontbold     = GetTheme(theme,"Font Bold","normal")
  fontstretch  = GetTheme(theme,"Font Stretch","normal")

  if linesettings["SIDE"] == "LEFT":
    xanchor = "end"
  else:
    xanchor = "start"
  lineheight = linesettings["LINESTEP"]

  # printPin - Draw the Pin Icon and Leader line

  if (message is not None) and (message != ""):
    dwg.add(dwg.text(
      message,
      (AnchorX + OffsetX, AnchorY + OffsetY + (lineheight/2)  ),
          font_size = fontsize, font_family=font, fill = fontcolor,
          font_style = fontslant,
          font_weight = fontbold,
          font_stretch = fontstretch,
          text_anchor=xanchor))   

  OffsetY += lineheight
  return ok

def EmbedGoogleFontLink(params):
  link   = param_to_str(params,1)

  if (link is not None):
    response = urllib.request.urlopen(link)
    fontdata = response.read().decode(response.info().get_param('charset'))
    dwg.defs.add(dwg.style(fontdata))
  else:
    print("ERROR: Must specify <link> for an embedded Font/s!")
    return False
  return True

def StartTextMessage(params):
  global messagesettings

  EndTextMessage()

  X = param_to_int(params, 1)
  Y = param_to_int(params, 2)
  messagesettings["LineStep"] = param_to_int(params, 3, messagesettings["LineStep"])
  messagesettings["Font"]     = param_to_str(params, 4, messagesettings["Font"])
  messagesettings["FontSize"] = param_to_int(params, 5, messagesettings["FontSize"])
  messagesettings["XJustify"] = param_to_str(params, 6, messagesettings["XJustify"])
  messagesettings["YJustify"] = param_to_str(params, 7, messagesettings["YJustify"])
  
  if X is not None:
    messagesettings["X"] = X
    messagesettings["OffsetX"] = 0
  
  if Y is not None:
    messagesettings["Y"] = Y
    messagesettings["OffsetY"] = 0

  if messagesettings["XJustify"] == "LEFT":
    xanchor = "start"
  elif messagesettings["XJustify"] == "RIGHT":
    xanchor = "end"
  else:
    xanchor = "middle"

  font = getFontTheme(messagesettings["Font"])

  messagesettings["SVGText"] = dwg.text(
      "",
      insert=(messagesettings["X"] + messagesettings["OffsetX"], 
      messagesettings["Y"] + messagesettings["OffsetY"]),
      font_size = themes[font]["FONT SIZE"], 
      font_family=themes[font]["FONT"], 
      stroke = themes[font]["OUTLINE COLOR"],
      fill = themes[font]["FONT COLOR"],
      font_style = themes[font]["FONT SLANT"],
      font_weight = themes[font]["FONT BOLD"],
      font_stretch = themes[font]["FONT STRETCH"],
      text_anchor = xanchor)
  return True

def writeText(params):
  global messagesettings

  if messagesettings["SVGText"] is None:
    print("ERROR: No multiline text message started!")
    return False

  font = getFontTheme(messagesettings["Font"])

  # Adds text to the multi line text message.
  EdgeColor = param_to_str(params,"none")
  Color = param_to_str(params,2,themes[font]["FONT COLOR"])
  Message = param_to_str(params,3,"")
  NL      = param_to_str(params,4,"")

  messagesettings["SVGText"].tspan(Message,
    stroke = EdgeColor,
    fill = Color)

  if NL == "NL":
    messagesettings["OffsetY"] += messagesettings["LineStep"]
    messagesettings["SVGText"].tspan("",
      insert=(messagesettings["X"] + messagesettings["OffsetX"], 
      messagesettings["Y"] + messagesettings["OffsetY"]))

  return True

def EndTextMessage(params=None):
  global messagesettings

  # Ends the multi line text message and embeds in the SVG.
  if messagesettings["SVGText"] is not None:
    dwg.add(messagesettings["SVGText"])
  messagesettings["SVGText"] = None
  return True

def drawBox(params):
  global themes

  ok = True
  theme = param_to_str(params,1)
  X = param_to_size(params,2)
  Y = param_to_size(params,3)
  Width = param_to_size(params,4)
  Height = param_to_size(params,5)
  justifyX   = param_to_str(params,6)
  justifyY   = param_to_str(params,7)
  message = param_to_str(params,8)

  pagedimensions = GetPageDimensions()

  if (Width is not None) and (Width < 1):
      Width = round(get_size(Width,pagedimensions[1][0]))
  if (Height is not None) and (Height < 1):
      Height = round(get_size(Height,pagedimensions[1][1]))

  if (theme is None):
    print("Box Theme name parameter missing!")
    ok = False

  if (X is None):
    print("Box X Location missing!")
    ok = False

  if (Y is None):
    print("Box Y Location missing!")
    ok = False

  if ((justifyX is not None) and (justifyX not in VALIDJUSTIFYX)):
    print("ERROR: <Justify X> must be one of {}".format(VALIDJUSTIFYX))
    ok = False

  if ((justifyY is not None) and (justifyY not in VALIDJUSTIFYY)):
    print("ERROR: <Justify Y> must be one of {}".format(VALIDJUSTIFYY))
    ok = False

  if (ok):
    TextBox(X, Y, "BOX_"+theme, message, justX=justifyX, justY=justifyY, W=Width, H=Height)

  return ok

def DefineFont(params):
  global themes
  fontname = param_to_str(params,1)
  if (fontname is None):
    print("Error: Must specify font name")
    return False
  themeentry = "FONT_"+fontname
  themes[themeentry] = {}
  themes[themeentry]["FONT"]            = param_to_str(params,2)
  themes[themeentry]["FONT SIZE"]       = param_to_int(params,3)
  themes[themeentry]["OUTLINE COLOR"]   = param_to_str(params,4,"none")
  themes[themeentry]["FONT COLOR"]      = param_to_str(params,5)
  themes[themeentry]["FONT SLANT"]      = param_to_str(params,6)
  themes[themeentry]["FONT BOLD"]       = param_to_str(params,7)
  themes[themeentry]["FONT STRETCH"]    = param_to_str(params,8)

  return True

def getFontTheme(fontname):
  if fontname in themes:
    return fontname
  return "FONT_"+fontname

csvCommands = {
  "SETUP" : {
    "DRAW"           : SetupDraw,
    "LABELS"         : SetLabels,
    "FILL COLOR"     : SetThemeStr,
    "OPACITY"        : SetThemeFloat,
    "BORDER COLOR"   : SetThemeStr,
    "BORDER WIDTH"   : SetThemeInt,
    "BORDER OPACITY" : SetThemeFloat,
    "FONT"           : SetThemeStr,
    "FONT SIZE"      : SetThemeInt,
    "FONT COLOR"     : SetThemeStr,
    "FONT SLANT"     : SetThemeStr,
    "FONT BOLD"      : SetThemeStr,
    "FONT STRETCH"   : SetThemeStr,
    "BOXES"          : SetThemeStr,
    "PAGE"           : SetPageSize,
    "DPI"            : SetDPI,
    "TYPE"           : SetPinType,
    "WIRE"           : SetWireType,
    "GROUP"          : SetPinGroup,
    "BOX"            : DefineBox,
    "TEXT FONT"      : DefineFont,
  },
  "DRAW" : {
    "GOOGLEFONT"  : EmbedGoogleFontLink,
    "IMAGE"       : writeImage,
    "ICON"        : writeIcon,
    "ANCHOR"      : moveAnchor,
    "PINSET"      : StartPinSet,
    "PIN"         : writePins,
    "PINTEXT"     : writePinText,
    "BOX"         : drawBox,
    "MESSAGE"     : StartTextMessage,
    "TEXT"        : writeText,
    "END MESSAGE" : EndTextMessage,
  }
}
    
def ReadCSV(fcsv, fsvg):
  """ CSV Format:
    \n  line enders
    ,   separates fields
    " " Quotes strings

    First Column is a command.
    Subsequent Columns are parameters to the command

    See README.md for command list
  """
  global dwg
  global svg_filename

  line = 0
  lineError = False

  svg_filename = str(fsvg)

  with fcsv.open() as csvfile :
    csvreader = csv.reader(csvfile, dialect='pinout')
    for row in csvreader:
      row = [entry.strip() for entry in row]  # Clean up extra spaces

      line = line + 1
      if ((EmptyRow(row)) or (row[0][0]=="#")):
        # ignore blank lines
        # And commented out commands
        continue
      try:
        lineError = not csvCommands[mode][row[0]](row)
      except KeyError:
         print("Error: Unknown {} Command!".format(mode))
         lineError = True

      if (lineError):
        lineError = False
        print("Line {}: {}".format(line,', '.join(row)))

  if (dwg is not None):
    dwg.save()

def main(arguments):
  csv.register_dialect('pinout',
                     escapechar='\\',
                     doublequote=False,
                     quoting=csv.QUOTE_MINIMAL,
                     lineterminator='\n',
                     skipinitialspace=True
                     )

  csv_file = Path(arguments['<filename.csv>'])

  if (arguments['<filename.svg>']):
    svg_file = Path(arguments['<filename.svg>'])
  else:
    # Make the filename if none given
    # Default to input file name with extension changed to .svg
    # and locate in a svg subdirectory
    svg_file = Path("svg/"+csv_file.stem + '.svg')

  # Make sure any path in the filename exists, and if not
  # create it.
  svg_file.parent.mkdir(parents=True, exist_ok=True)

  overwrite = arguments['--overwrite']
  file_error = False

  if (not csv_file.is_file()):
    print("ERROR: CSV File {} can not be found!".format(csv_file))
    file_error = True

  if (svg_file.is_file() and not overwrite):
    print("ERROR: SVG File {} Exists.  Can not Overwrite without --overwrite option!".format(svg_file))
    file_error = True

  if (file_error):
    print("Fatal File Error!  Exiting.")
    exit(1)

  ReadCSV(csv_file, svg_file)

if __name__ == "__main__":
    # execute only if run as a script
    arguments = docopt(__doc__, version=VERSION)
    main(arguments)
