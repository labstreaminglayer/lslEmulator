from AxonCommon import AxonCommon, State
import sys
import time
from enum import Enum
import random
import serial
from pylsl import StreamInfo, StreamOutlet
import numpy

class MockSerial:
  port: str
  baudrate: int
  timeout: int
  def open(self):
    pass
  def write(self, bytes: bytes):
    pass

  def read_until(self) -> bytes:
    # b'\x1a\xda\xc7\x88'
    x = bytearray(b"\r")
    x.extend(random.randbytes(17))
    x.extend(b"\n")
    return bytes(x)
  def read(self, size):
    return 0
  def flush(self):
    pass

class EmulatorCOM(AxonCommon):
  inputThreadAlive = True
  ser = MockSerial()
  ser.baudrate = 2304000
  ser.timeout = 5
  num_modules = 0
  scenario = 0
  # def __init__(self):
  #   self.val = 0
  port: str
  def init(self):
    # neat to emulate it already streaming
    # when hitting init
    # b'\r12111111111111111\n'
    time.sleep(.1)
    self.ser.write(b"p")
    iPack = self.ser.read_until()
    msg = ""
    try:
      if iPack[0].to_bytes(1, 'big') != b'\r':
        self.state = State.disconnected
        msg = "No CR on beginning"
      if iPack[18].to_bytes(1, 'big') != b'\n':
        msg = "No NL on end"
        self.state = State.disconnected
      if len(iPack) != 19:
        self.state = State.disconnected
        msg = "init packet wrong length"
      if msg != "":
        print(msg)
        return
      self.handleInitPack(iPack)
    except Exception as e:
      print("Init packet error: " + str(e))
      self.ser.write(b"h")
      self.ser.flush()
      self.ser.write(b"c")
      exit()

  def halt(self):
    self.state = State.connected

  def connect(self, comTrgt):
    # print("trying to connect [mock]")
    self.ser.port = comTrgt
    try:
      self.ser.open()
      self.state = State.connected
    except Exception as e:
      self.state = State.disconnected
      msg = "error open serial port: " + str(e)
      print(msg)
      return msg
    if(self.state == State.connected):
      self.init()
      return []
  # lsl - outlet.push()
  # info creates a 
  # creating a stream output with it, it
  # sets an lsl. Basiclaly, a fancy socket anyone can connect to
  # fancy because anything it connects to will know how many channels, 
  # all pretty under the hood
  # pushing data using outlet.push_smaple() 
  # shape of data should match the data
  def handleInitPack(self, pack):
    self.num_modules = 1
    self.channels = self.num_modules*8
    # pass
    # CLI 
  def stream(self):
    if(not self.state.streaming):
      return False
    time.sleep(0.1)
    self.ser.write(b'b')
    time.sleep(0.1)
    # set up lsl
    name = "AxonEEG"
    type = "EEG"
    srate = 250
    info = StreamInfo(name, type, self.channels, srate, "float32", "myuid34234")
    outlet = StreamOutlet(info)
    self.ser.flush()
    incomingSize = 5+24*self.num_modules
    self.state=State.streaming
    b_order = 6
    fs = 250.0  # sample rate, Hz
    low_cutoff = 15.0  # desired cutoff frequency of the filter, Hz
    high_cutoff = 1.0  # desired cutoff frequency of the filter, Hz
    notch_center = 60.0  # desired frequency to remove with notch filter, Hz
    counter = 0
    pps = 50            # estimated packets per second
    delay = 1 / pps     # delay to use between sending packets
    while self.state==State.streaming:
      smpl = numpy.random.uniform(low=0.5, high=2000.5, size=(self.num_modules*8,))
      outlet.push_sample(smpl.tolist())
      time.sleep(delay)

    # print('stopping...')
    # self.ser.write(b'c')
    # if(self.state == State.closing):
    #     sys.exit()
    print(self.state)
    # self.state = State.connected
    time.sleep(random.randrange(1, 10)/100)

  def stopStream(self):
    print("changing state")
    self.state = State.connected

