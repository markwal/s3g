# Gcode parser, 

from errors import *
import time

def ExtractComments(line):
  """
  Parse a line of gcode, stripping semicolon and parenthesis-separated comments from it.
  @param string line gcode line to read in
  @return tuple containing the non-comment portion of the command, and any comments
  """

  # Anything after the first semicolon is a comment
  semicolon_free_line, x, comment = line.partition(';')

  command = ''

  paren_count = 0
  for char in semicolon_free_line:
    if char == '(':
      paren_count += 1

    elif char == ')':
      if paren_count < 1:
        raise CommentError

      paren_count -= 1

    elif paren_count > 0:
      comment += char

    else:
      command += char
   
  return command, comment

def ParseCommand(command):
  """
  Parse the command portion of a gcode line, and return a dictionary of code names to
  values.
  @param string command Command portion of a gcode line
  @return dict Dictionary of commands, and their values (if any)
  """
  registers = {}

  pairs = command.split()
  for pair in pairs:
    code = pair[0]

    # If the code is not a letter, this is an error.
    if not code.isalpha():
      raise InvalidCodeError()

    # Force the code to be uppercase.
    code = code.upper()

    # If the code already exists, this is an error.
    if code in registers.keys():
      raise RepeatCodeError()

    # Don't allow both G and M codes in the same line
    if ( code == 'G' and 'M' in registers.keys() ) or \
       ( code == 'M' and 'G' in registers.keys() ):
      raise MultipleCommandCodeError()

    # If the code doesn't have a value, we consider it a flag, and set it to true.
    if len(pair) == 1:
      registers[code] = True

    else:
      registers[code] = float(pair[1:])

  return registers

def ParseLine(line):
  """
  Parse a line of gcode into a map of registers, and a comment field.
  @param string line line of gcode to parse
  @return tuple containing an array of registers, and a comment string
  """

  command, comment = ExtractComments(line)
  registers = ParseCommand(command)

  return registers, comment


class GcodeStateMachine():
  """
  Read in gcode line by line, tracking some state variables and running known
  commands against an s3g machine.
  """
  def __init__(self):
    self.position = {    # Current machine position
        'X' : 0,
        'Y' : 0,
        'Z' : 0,
        'A' : 0,
        'B' : 0,
        }
    self.offsetPosition = {}
    self.offset_register = None     # Current offset register, if any
    self.toolhead = None               # Tool ID
    self.toolheadDict = {
        0   :   'A',
        1   :   'B',
        }
    self.toolhead_speed = None         # Speed of the tool, in rpm???
    self.toolhead_direction = None # Tool direction; True=forward, False=reverse
    self.toolhead_enabled = None # Tool enabled; True=enabled, False=disabled
    self.s3g = None
    self.rapidFeedrate = 300
    self.findingTimeout = 60 #Seconds

  def SetOffsets(self, registers):
    """Given a set of registers, sets the offset assigned by P to be equal to those axes in registers.  If the P register is missing, OR the register is considered a flag, we raise an exception.

    @param dict registers: The registers that have been parsed out of the gcode
    """
    if 'P' not in registers:
      raise MissingRegisterError
    elif isinstance(registers['P'], bool):
      raise InvalidRegisterError
    self.offsetPosition[registers['P']] = {}
    for axis in self.ParseOutAxes(registers):
      self.offsetPosition[registers['P']][axis] = registers[axis]

  def SetPosition(self, registers):
    """Given a set of registers, sets the state machine's position's applicable axes values to those in registers.  If a register is set as a flag, that register is disregarded
   
    @param dictionary registers: A set of registers that have updated point information
    """
    for key in registers:
      if key in self.position:
        if not isinstance(registers[key], bool):
          self.position[key] = registers[key]

  def ApplyNeededOffsetsToPosition(self):
    """Given a position, applies the applicable offsets to that position
    @param dict position: The position to apply offsets to
    """
    if self.toolhead != None:
      for key in self.offsetPosition[self.toolhead]:
        self.position[key] += self.offsetPosition[self.toolhead][key]

  def LosePosition(self, registers):
    axes = self.ParseOutAxes(registers)
    for axis in axes:
      self.position[axis] = None

  def ExecuteLine(self, command):
    """
    Execute a line of gcode
    @param string command Gcode command to execute
    """

    # Parse the line
    registers, comment = ParseLine(command)

    # Update the state information    
    if 'G' in registers:
      if registers['G'] == 0:
        self.SetPosition(registers)
        self.ApplyNeededOffsetsToPosition()
        self.RapidPositioning()
      elif registers['G'] == 1:
        if 'E' in registers:
          if 'A' in registers or 'B' in registers:
            raise LinearInterpolationError
          else:
            self.InterpolateERegister(registers)
            self.SetPosition()
            self.ApplyNeededOffsetsToPosition()
            #self.SendPointToMachine()
        else:
          self.SetPosition(registers)
          self.ApplyNeededOffsetsToPosition()
          #self.SendPointToMachine()
      elif registers['G'] == 4:
        self.Dwell(registers)
      elif registers['G'] == 10:
        self.SetOffsets(registers)
      elif registers['G'] == 54:
        self.toolhead = 0
      elif registers['G'] == 55:
        self.toolhead = 1
      elif registers['G'] == 92:
        self.SetPosition(registers)
        self.ApplyNeededOffsetsToPosition()
        self.RapidPositioning()
      elif registers['G'] == 161:
        self.LosePosition(registers)
        #self.FindAxesMinimums(registers)
      elif registers['G'] == 162:
        self.LosePosition(registers)
        #self.FindAxesMaximums(registers)
    elif 'M' in registers:
      if registesr['M'] == 6:
        pass
        #self.WaitForToollhead(registers)
      elif registers['M'] == 18:
        #self.DisableAxes(registers)
      elif registers['M'] == 70:
        self.DisplayMessage(registers)
      elif registers['M'] == 71:
        self.DisplayMessageButonWait(registers)
      elif registers['M'] == 72:
        self.QueueSong(registers)
      elif registers['M'] == 73:
        self.SetBuildPercentage(registers)
      elif registers['M'] == 101:
        self.toolhead_enabled = True
        self.toolhead_direction = True
      elif registers['M'] == 102:
        self.toolhead_enabled = True
        self.toolhead_direction = False
      elif registers['M'] == 103:
        self.toolhead_enabled = False
      elif registers['M'] == 104:
        self.SetToolheadTemperature(registers)
      elif registers['M'] == 109:
        self.SetPlatformTemperature(registers)
      elif registers['M'] == 108:
        if 'R' not in registers:
          raise MissingRegisterError
        if isinstance(registers['R'], bool):
          raise InvalidRegisterError
        self.toolhead_speed = registers['R']
      elif registers['M'] == 132:
        self.LosePosition(registers)
        self.RecallHomePosition(registers)
    
    # Run the command
    if 'G' in registers.keys():
      GCodeInterface = {
          #0     :     self.RapidPositioning,
          #1     :     self.LinearInterpolation,
          #4     :     self.Dwell,
          #130   :     self.SetPotentiometerValues,
          #161   :     self.FindAxesMinimums,
          #162   :     self.FindAxesMaximums,
          }
      try:
        GCodeInterface[registers['G']](registers, comment)
      except KeyError:
        pass
    elif 'M' in registers.keys():
      MCodeInterface = {
          #6     :     self.WaitForToolhead,
          #18    :     self.DisableAxes,
          #70    :     self.DisplayMessage,
          #71    :     self.DisplayMessageButtonWait,
          #72    :     self.QueueSong,
          #73    :     self.SetBuildPercentage,
          #104   :     self.SetToolheadTemperature,
          #109   :     self.SetPlatformTemperature,
          #132   :     self.RecallHomePosition,
          }
      try: 
        MCodeInterface[registers['M']](registers, comment)
      except KeyError:
        pass
    else:
      print 'Got no code?'


  def ParseOutAxes(self, registers):
    """Given a set of registers, returns a list of all present axes

    @param dict registers: Registers parsed out of the gcode command
    @return list: List of axes in registers
    """
    possibleAxes = ['X', 'Y', 'Z', 'A', 'B']
    return [axis for axis in registers if axis in possibleAxes]

  def GetPoint(self):
    return [
            self.position['X'], 
            self.position['Y'], 
            self.position['Z'],
           ]

  def GetExtendedPoint(self):
    return [
            self.position['X'], 
            self.position['Y'], 
            self.position['Z'], 
            self.position['A'], 
            self.position['B'],
           ]

  def RapidPositioning(self, registers, comment):
    """Moves at a high speed to a specific point

    @param dict registers: Registers parsed out of the gcode command
    @param string comment: Comment associated with the gcode command
    """
    self.s3g.QueuePoint(self.GetPoint(), self.rapidFeedrate)

  def Dwell(self, registers):
    """Can either delay all functionality of the machine, or have the machine
    sit in place while extruding at the current rate and direction.

    @param dict registers: Registers parsed out of the gcode command
    @param string command: Comment associated with the gcode command
    """
    if self.toolhead_enabled:
      if self.toolhead_direction:
        delta = self.toolhead_speed
      else:
        delta = -self.toolhead_speed
      startTime = time.time()
      while time.time() < startTime + registers['P']:
        self.position[self.toolheadDict[self.toolhead]] += delta
        RPS = self.toolhead_speed / 60.0
        RPMS = self.toolhead_speed / RPS
    else:
      microConstant = 1000000
      miliConstant = 1000
      self.s3g.Delay(registers['P']*(microConstant/miliConstant))

  def PositionRegister(self):
    """Gets the current extended position and sets the machine's position to be equal to the modified position
    """ 
    self.s3g.SetExtendedPosition(self.GetExtendedPoint()) 

  def SetPotentiometerValues(self, registers):
    """Given a set of registers, sets the machine's potentiometer value to a specified value in the registers

    @param dict registers: Registers parsed out of the gcode command
    """
    #Put all values in a hash table
    valTable = {}
    #For each register in registers thats an axis:
    for a in self.ParseOutAxes(registers):
      #Try to append it to the appropriate list
      try:
        valTable[int(registers[a])].append(a.lower())
      #Never been encountered before, make a list
      except KeyError:
        valTable[int(registers[a])] = [a.lower()]
    for val in valTable:
      self.s3g.SetPotentiometerValue(valTable[val], val)

  def FindAxesMinimums(self, registers):
    axes = [axis.lower for axis in self.ParseOutAxes(registers)]
    self.s3g.FindAxesMinimums(axes, ['F'], self.findingTimeout)
