import sys
import time
from enum import Enum
import serial
# from pylsl import StreamInfo, StreamOutlet
import numpy
from signal_processing import butter_lowpass_filter, butter_highpass_filter, iir_notch_filter

class State(Enum):
    disconnected = 0
    connected = 1
    streaming = 2
    stopping = 3
    error = 4
    closing = 5

class AxonController():
    inputThreadAlive = True
    state:State = State.disconnected
    ser = serial.Serial()
    ser.baudrate = 230400
    ser.timeout = 5
    commands = {}
    num_modules = 0
    def __init__(self):
        commands = {
            # TODO implement this so they can connect to a different com in one go
            'c': self.halt,
            'b': self.stream,
            'h': self.halt,
        }

    def halt(self):
        self.state = State.connected

    def connect(self, comTrgt):
        self.ser.port = comTrgt

        try:
            self.ser.open()
            self.state = State.connected
        except Exception as e:
            self.state = State.disconnected
            print("error open serial port: " + str(e))
            return "error open serial port: " + str(e)
        if(self.state==State.connected):
            self.init()
    # def handleInitPack(self, pack):

    def init(self):
        # self.ser.flush()
        # self.ser.write(b'c')
        # self.ser.flush()
        # self.ser.write(b'c')
        # self.ser.flush()
        time.sleep(0.1)
        self.ser.write(b"p")
        iPack = self.ser.read_until()
    #     TODO handle init packet
    #     channels = 8
        # self.num_modules = 1
        try:
            # print(init_pckt[0].to_bytes())
            if iPack[0].to_bytes(1, 'big') != b'\r':
                self.state = State.disconnected
                print("No CR on beginning")
                print(iPack)
                return

            # print(init_pckt[17].to_bytes())
            if iPack[17].to_bytes(1, 'big') != b'\n':
                self.state = State.disconnected
                print("No NL on end")
                print(iPack)
                return

            # print(len(init_pckt))
            if len(iPack) != 18:
                self.state = State.disconnected
                print("init packet wrong length")
                return
            self.handleInitPack(iPack)
            # print("Init packet formatted correctly")
        except Exception as e:
            print("Init packet error: " + str(e))
            self.ser.write(b"h")
            self.ser.flush()
            self.ser.write(b"c")
            exit()

    def handleInitPack(self, pack):
        cleaned = pack.strip().decode('utf-8')
        self.num_modules = cleaned.count('2')
        self.channels = self.num_modules*8

    def stopStream(self):
        print('changing state')
        self.state = State.connected

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
        # info = StreamInfo(name, type, self.channels, srate, "float32", "myuid34234")
        # outlet = StreamOutlet(info)
        self.ser.flush()
        incomingSize = 5+24*self.num_modules

        b_order = 6
        fs = 250.0  # sample rate, Hz
        low_cutoff = 15.0  # desired cutoff frequency of the filter, Hz
        high_cutoff = 1.0  # desired cutoff frequency of the filter, Hz
        notch_center = 60.0  # desired frequency to remove with notch filter, Hz
        counter = 0
        while self.state==State.streaming:
            incoming = self.ser.read(incomingSize).hex()
            line = incoming[2:]
            n = 6
            chunks = [line[i:i + n] for i in range(0, len(line), n)]
            rawSample = numpy.array([int(chunks[i], 16) / 9000 for i in range(0, 8 * self.num_modules)])
            sample = rawSample
            # for chan in range(0, len(rawSample)):
            data = rawSample
            # data = rawSample[:,chan] - np.mean(rawSample[:,chan])
            y = butter_lowpass_filter(data, low_cutoff, fs, b_order)
            y = butter_highpass_filter(y, high_cutoff, fs, b_order)
            sample = iir_notch_filter(y, notch_center, fs)
                # print("sample", file=sys.stdout)
                # print(sample, file=sys.stdout)
                # print("sample")
            print(sample)
            # outlet.push_sample(sample.tolist())
        print('stopping...')
        self.ser.write(b'c')
        # print(f'state is {self.state}')
        if(self.state == State.closing):
            sys.exit()
        print(self.state)
        self.state = State.connected

    def handleCommand(self, command, repSer):
        cleanCommand = command.replace('\r\n','').replace('\n', '');
        if(len(cleanCommand)>1):
            # connect or bad
            if("connect "in cleanCommand):
                target = cleanCommand.split(' ')[1]
                print('connecting...')
                connected = self.connect(target)
                if len(connected)<8:
                    response = f"connect response: success"
                else:
                    response = f"connect response: {connected}"
                repSer.send(str.encode(response))
        else:
            if(self.state!=State.disconnected):
                if(cleanCommand=='h'):
                    if(self.state==State.streaming):
                        print("halting...")
                        self.state = State.connected
                    else:
                        print("stream is not running")
            if(cleanCommand=='p'):
                print('init...')
                if(self.state!= State.connected):
                    message = "cannot init. Not connected. Connect first."
                    print(message)
                    repSer.send(str.encode(message))
                else:
                 self.init()
            if (cleanCommand == 'c'):
                print("killing...")
                self.state = State.closing
                if(not self.state==State.streaming):
                    self.inputThreadAlive = False
                    sys.exit()
            if(cleanCommand=='b'):
                print('streaming...')
                self.state = State.streaming
            # self.commands[cleanCommand](self)