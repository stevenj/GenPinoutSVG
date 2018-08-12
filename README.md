# GenPinoutSVG

This repository contains a program to produce pinout SVG files from a CSV file
source file of pin defintions and other graphical/format commands.

This program was inspired by [https://github.com/sparkfun/Graphical_Datasheets]

## How To Use

This is a Python 3 program and has only been tested on V3.6.  It should be 
considered the minimum version for bug reports.

1. Create a Python Virtual Environment
2. Install Dependencies with pip
    * docopt
    * svgwrite
    * wand
3. Clone this repository
4. Execute ./GenPinoutSVG.py \<csv file\>

## CSV Input data format

The CSV format is a simple list of drawing commands, at a higher level than raw SVG and targeted to the needs of a graphical pinout datasheet.

The basic format of the CSV file is:

* \n (Carriage Return 0x13) is the Line Ender character
* Fields are seperated with , (Comma)
* If you put a comma inside a string, quote it with " (double quote)
  
Each line of the CSV is a command, with the following general format:

* First Field = Command Name
* Second to Nth Field = Options to the command
  
There are **TWO** Phases in the drawing process and the commands are divided by phase.  The first phase is the SETUP phase, which defines all the attributes of the page and drawing options, themes.  The Second phase is the DRAW phase and it is triggered by the DRAW command.

DRAW Operations must occur in Draw Phase and Setup operations must occur in Setup phase.

### **SETUP** Phase Commands (Called before the **DRAW** Command)

* **LABEL**, DEFAULT, TYPE, GROUP, \<list of labels for pin attributes\>
  * Defines PIN labels, best as the first command in the file. Aligns with pin data draw commands in draw phase.  Helps create named columns which ease editing in a spreadsheet.
    * DEFAULT - Defines the Default theme
    * TYPE - Pin Type Theme Settings
    * GROUP - Pin Group Theme Settings
    * \<List> - The List of PIN Functions
* **BORDER COLOR**,  default, \<type>, \<group>, \<List of border colors for each label>
  * Defines Theme border color of Pin Type
    * DEFAULT - Default border color, must be specified
    * \<type> - Optional border color for Types
    * \<group> - Optional border color for Pin Groups
    * \<list> - Optional border color for each Pin Label
* **FILL COLOR**, default, \<type>, \<group>, \<List of fill colors for each label>
  * Defines Theme fill color of Pin Type
    * DEFAULT - Default fill color, must be specified
    * \<type> - Optional fill color for Types
    * \<group> - Optional fill color for Pin Groups
    * \<list> - Optional fill color for each Pin Label
* **OPACITY**, default, \<type>, \<group>, \<List of opacities for each label>
  * Theme Opacity Value of Pin Type
    * DEFAULT - Default fill color opacity, must be specified
    * \<type> - Optional fill color opacity for Types
    * \<group> - Optional fill color opacity for Pin Groups
    * \<list> - Optional fill color opacity for each Pin Label
* **FONT** \default, \<type>, \<group>, \<List of font names for each label>
  * Theme Font of Pin Type
    * DEFAULT - Default Font, must be specified
    * \<type> - Optional Font for Types
    * \<group> - Optional Font for Pin Groups
    * \<list> - Optional Font for each Pin Label 
* **FONT SIZE**,     <default>, <type>, <group>, <List of font sizes for each label>                        - Theme
* **FONT COLOR**,    <default>, <type>, <group>, <List of font colors for each label>                       - Theme
* **FONT SLANT**,    <default>, <type>, <group>, <List of font colors for each label>                       - Theme - 0 = Normal 1 = Slight 
* Slant, 2 = Most Slant
* **FONT BOLD**,     <default>, <type>, <group>, <List of font colors for each label>                       - Theme - 1 = Normal <1 = Lighter >1<2 = Darker 2=Darkest
* **FONT STRETCH**,  <default>, <type>, <group>, <List of font colors for each label>                       - Theme - 1 = Normal <1 = Condensed >1<2 = Expanded 2=Most Expanded 0 = Most Condensed
* **CORNER RX**,     <default>, <type>, <group>, <List of X Corner Radius for each label>                   - Theme
* **CORNER RY**,     <default>, <type>, <group>, <List of Y Corner Radius for each label>                   - Theme
* **X ALIGN**,       <default>, <type>, <group>, <List of X Alignments for each label>                      - Theme
* **Y ALIGN**,       <default>, <type>, <group>, <List of Y Alignments for each label>                      - Theme
* **SKEW**,          <default>, <type>, <group>, <list of box skews for each label>                         - Theme
* **SKEW SHIFT**     <default>, <type>, <group>, <list of shifts to compensate box translation due to skew> - Theme
* **WIDTH**          <default>, <type>, <group>, <list of box widths>
* **HEIGHT**         <default>, <type>, <group>, <list of box heights>
* **TYPE**, **IO**, <Color>, <Opacity>          - Sets the Color and Opacity of the Leader Line for an IO pin
* **TYPE**, **INPUT**, <Color>, <Opacity>       - Sets the Color and Opacity of the Leader Line for an INPUT pin
* **TYPE**, **OUTPUT**, <Color>, <Opacity>      - Sets the Color and Opacity of the Leader Line for an OUTPUT pin
* **TYPE**, **PWM**, <Color>, <Opacity>         - Sets the Color and Opacity of the Leader Line for an PWM pin
* **TYPE**, **ANALOG**, <Color>, <Opacity>      - Sets the Color and Opacity of the Leader Line for an ANALOG pin
* **GROUP**, <name>, <Color>, <Opacity>     - Sets the Name of a Pin group, and the Color and Opacity of the Pin Group Circle.
* **BOX**, \<Name>, \<Border Color>, \<Border Opacity>, \<Fill Color>, \<Fill Opactiy>, \<Linewidth>, \<BoxWidth>, \<BoxHeight>, \<Box Cr X>, \<Box Cr Y>, \<Box Skew>, \<Box Skew Offset>
    * Define a box theme
        * Name - The name of the box theme
        * Border Color - The color of the Border line around the box
        * Border Opacity - Number 0.00-1.00 defines opacity of the border line
        * Fill Color - Fill color of the box
        * Fill Opacity - Opacity of the Fill (0.00-1.00), set to 0 for no fill
        * Line Width - Width of the border line
        * Box Width - Default width of the box
        * Box Height - Default height of the box
        * Box Cr X - Box Corner Radius (X Direction)
        * Box Cr Y - Box Corner Radius (Y Direction)
        * Box Skew - Amount of slant to pu on the box
        * Box Skew Offset - Horizontal correction size to realign slanted box to unslanted box.
* **TEXT FONT**, <Name>, <Size>, <Outline Color>, <Color>, <slant>, <bold>, <stretch> - Defines a Font for use by text entries. Text entries can also use a font theme for a labeled pin column
* **PAGE**, "page name" - Sets the page size Defaults to A4L)
* **DPI**, num - Sets the dots per inch. (Defaults to 300)
* **DRAW** - Starts the Page Draw, Setup commands after this are ignored.  Draw commands before this are ignored.

### **DRAW** Phase Commands (Called before the **DRAW** Command)

* **GOOGLEFONT**, <link>                            - Embed a link to google web fonts (doesn't work for Inkscape)
* **IMAGE**, name, X, Y, W, H, <cx>, <cy>, <cw>, <ch>, <rot> - Puts a PNG on the page at the requested location and for the requested size, with an optional crop and rotate.
* **ICON**, name.svg, X,Y,W,H,<rot>                 - Embeds another SVG inside this one. (Used for icons)
* **ANCHOR**, X, Y                            - Sets Starting point for Pin Attribute prints.
* **PINSET** <Side>, <Packed> <JustifyX>, <JustifyY>, <LineStep>, <LeaderOffset>, <Column Gap>, <LeaderHStep> - Define a pin list. - LeaderHStep allows the leader to be offset each line for vertical pins.
* **PIN**, <Icon>, <TYPE>, <GROUP>, <List of Pin attribute strings> - Pin Attributes to print at next pin line.
* **PINTEXT**, <Icon>, <TYPE>, <GROUP>, <Text> - Text to print at next pin line.
* **BOX**, Theme, X, Y, \<BoxWidth>, \<BoxHeight>, \<X Justify>, \<Y Justify>, \<Text> 
    * Draw a box at the required location.
        * Theme - The box theme to draw with.
        * X,Y - The Origin of the box (Top Left corner)
        * Width/Height - Optional, if set override the themes box size
        * X Justify - Optional, define Text justification in box, valid options are "LEFT", "RIGHT", "CENTER", defaults to "CENTER" if not set.
        * Y Justify - Optional, define Text justification in box, valid options are "TOP", "BOTTOM", "CENTER", defaults to "CENTER" if not set.
        * Text - Optional, Text to place inside the box.
* **MESSAGE**, <X>, <Y>, <Line Step>, <Font>, <Font Size> - Text Message Options.  Any missing options use the previously set value, and do not reset.
* **TEXT**, <edge color>, <color>, <Message>, <NL> - Arbitrary Line of Text, using MESSAGE options.

## License

This code is licensed under GPL-3.  See [GPL-3](gpl-3.0.md) for Details.
