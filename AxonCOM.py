import sys
import time
from enum import Enum
if sys.platform == "win32":
    from serial.serialwin32 import Serial as Serial
else:
    from serial.serialposix import Serial as Serial
from pylsl import StreamInfo, StreamOutlet
import numpy
import threading
from AxonCommon import AxonCommon, State
# from signal_processing import butter_lowpass_filter, butter_highpass_filter, iir_notch_filter
from axontools import PcktType

class AxonCOM(AxonCommon):


    ser = Serial()
    serial_lock = threading.Lock()
    streaming_lock = threading.Lock()
    ser.baudrate = 230400
    ser.timeout = 5
    num_modules = 0

    def halt(self):
        self.safe_serial_write(b'c')
        time.sleep(1)
        self.inputThreadAlive = False
        # self.state = State.connected
        # print(f'After: {self.state}')
        # try:

            # self.ser.write(b"c")
        # except Exception as e:
            # print(f"COuld not kill/write to kill: {str(e)}")
        # print('Just wrote "c"')

    def connect(self, comTrgt):
        self.ser.port = comTrgt

        try:
            self.ser.open()
            self.state = State.connected
            return 'success'
        except Exception as e:
            self.state = State.disconnected
            print("error open serial port: " + str(e))
            return "error open serial port: " + str(e)
        # if(self.state==State.connected):
        #     self.init()
    # def handleInitPack(self, pack):
    
    def removeBias(self):
        self.safe_serial_write(b'm100.')
        # time.sleep(1)
        # self.ser.flush()
        # time.sleep(1)
        return 1
    def safe_serial_write(self, data):
        with self.serial_lock:
            self.ser.write(data)
            self.ser.flush()
    def safe_serial_read(self, timeout=2.0, size=0):
        try:
            with self.serial_lock:
                self.ser.timeout = timeout
                if(size>0):
                    data = self.ser.read_until(size=size)
                else:
                    data = self.ser.read_until()
                return data if data else b""
        except Exception as e:
            print("Errror reading: ", str(e))
            return b""
    
    def safe_serial_reset_buffers(self):
        with self.serial_lock:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()

    def calibrate(self):
        incomingSize = 5+24*self.num_modules

        while True:
            self.safe_serial_write(b"k1")

            # Recieves the confirmation that voltage calibration mode is enabled. 
            res = self.safe_serial_read()
            print(res)
            if b"Enabled voltage calibration mode." not in res:
                print("Module was already in vcal mode, trying again.")
                continue
            else: 
                print("Enabled vcal mode")
                break

        # Prepare the arrays for recording
        vcal_samples = 500
        vcal_data = numpy.zeros((vcal_samples, self.num_modules*8), dtype='int')
        vcal_num_avgd = 100
        counter = 0
    
        # Start the voltage calibration process
        self.safe_serial_write(b'b')
        try: 
            while True:
                # print("printing...")
                while True:
                    if self.ser.read() == b"\r":
                        break
                    
                pckt_type_byte = self.safe_serial_read(size=1).hex()
                pckt_type = int(bytearray.fromhex(pckt_type_byte).decode("utf-8"), 16)
                # print(f"{pckt_type} + {PcktType(pckt_type).name}")
                
    
                if pckt_type == PcktType.DATA.value:
                    incoming = self.ser.read(incomingSize).hex()
    
                    line = incoming[2:]
                    sample_num = int.from_bytes(bytearray.fromhex(incoming[0:2]), byteorder='big')
                    n=6
                    chunks = [line[i:i + n] for i in range(0, len(line), n)]
                    rawSample = numpy.array([self.convertReading(chunks[i]) for i in range(0, 8 * self.num_modules)])
                    sample = rawSample
    
                    # Code to save each sample into the array. 
                    vcal_data[counter] = sample
    
                    # Read the ending of the packet and extract the status bytes and battery level
                    endbytes = incoming[-8:]
    
                    # if sample_num == 60:
                    # print(f"Sample num: {sample_num} | End bytes: {endbytes}")
                    status1 = int.from_bytes(bytearray.fromhex(incoming[-8:-6]), byteorder='big')
                    status2 = int.from_bytes(bytearray.fromhex(incoming[-6:-4]), byteorder='big')
                    battlvl = int.from_bytes(bytearray.fromhex(incoming[-4:-2]), byteorder='big') - 64
                    # print(f"Status1 {status1}, Status2 {status2}, Battery level {battlvl}")
                    if counter % 2000 == 0:
                        print(f"Battery level: {battlvl}")
                    
                elif pckt_type == PcktType.INIT.value:
                    raise Exception("Init packet received again, something is wrong.")
                elif pckt_type == PcktType.PADDING.value:
                    raise Exception("Padding packet received, something is wrong.")
                elif pckt_type in {PcktType.DEBUG.value, PcktType.INFO.value, PcktType.WARNING.value, PcktType.ERR.value, PcktType.FATAL.value}:
                    incoming = self.safe_serial_read().hex()
                    message = bytearray.fromhex(incoming[2:-2]).decode("utf-8")
                    print(f"{PcktType(pckt_type).name} pckt: \"{message}\"")
                else: 
                    raise Exception(f"Unknown packet type received. Packet type: {pckt_type}")
                
                counter+=1
    
                if counter >= vcal_samples:
                    break
                    
        except KeyboardInterrupt:
            print("Cancelled by user")
            
        # except Exception as e:
        #     print("Error: " + str(e))
            
        finally:
            print("Stopping calibration stream")
            self.safe_serial_write(b"c")
            time.sleep(.4)
            self.safe_serial_reset_buffers()

            # Wait until the module is back into init mode.
            res = self.safe_serial_read()

            while True:
                self.safe_serial_write(b"k0")
                
                # Recieves the confirmation that voltage calibration mode is disabled. 
                res = self.safe_serial_read()
                # print(res)
                if b"Disabled voltage calibration mode." not in res:
                    # print("Module was already not in vcal, trying again.")
                    continue
                else: 
                    print("Disabled vcal mode")
                    break
        # Start analyzing the voltage calibration data. 
        print("Analyzing voltage calibration data...")
        # Steps:
        # 1. Find the zero-crossing points
        # 2. Remove points around the zero-crossings
        # 3. Separate the positive and negative values
        # 4. Calculate the average of the positive and negative values
        # 5. The amplitude is the difference between the average positive and average negative values
    
        # Find zero-crossing points
        zero_crossings = numpy.where(numpy.diff(numpy.sign(vcal_data[:, 0]), axis=0))[0]
        # print(f"Zero-crossing points: {zero_crossings}")
    
        # Remove points around the zero-crossings
        margin = 3  # Number of points to remove around zero-crossings
        for zero_crossing in zero_crossings:
            start = max(0, zero_crossing - margin)
            end = min(vcal_data.shape[0], zero_crossing + margin)
            vcal_data[start:end, :] = 0
    
        # Separate positive and negative values
        positive_row_indices = numpy.where(vcal_data[:, 0] > 0)[0]
        negative_row_indices = numpy.where(vcal_data[:, 0] < 0)[0]
    
        positive_values = vcal_data[positive_row_indices, :]
        negative_values = vcal_data[negative_row_indices, :]
    
        # Calculate the average of the positive and negative values
        davg_p = numpy.round(numpy.mean(positive_values, axis=0))
        davg_n = numpy.round(numpy.mean(negative_values, axis=0))
        self.c_factor = numpy.round(1875 / (davg_p - davg_n), 6)
    
        # # Write all of the samples into a csv file for testing. 
        # time_now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        # output_file = f'./test_outputs/vcal_test_{time_now}.csv'
        # with open(output_file, 'w', newline='') as csvfile: 
        #     streamwriter = csv.writer(csvfile, delimiter=',', dialect='excel')
            
        #     for i in range(0, np.shape(vcal_data)[0]):
        #         streamwriter.writerow(vcal_data[i])
    
        print("Voltage calibration complete")
        print(f"Calibration factors: {self.c_factor}")
    
    def init(self):
        # self.ser.flush()
        # self.ser.write(b'c')
        # self.ser.flush()
        # time.sleep(1)
        # iPack = self.ser.read_until()
        # if iPack != b'':
        #     print(iPack)
            # self.halt()
            
            # self.ser.write(b'h')
            # self.ser.flush()
            # time.sleep(1)
            # self.ser.write(b'c')
            # time.sleep(1)
        #     # time.sleep(3)
        self.safe_serial_write(b'p')
        # time.sleep(1)
        # [ ] maybe add "are you streaming call to the board??"
        iPack = self.safe_serial_read()
    #     TODO handle init packet
    #     channels = 8
        # self.num_modules = 1
        msg = ""
        try:
            # print(init_pckt[0].to_bytes())
            if iPack[0].to_bytes(1, 'big') != b'\r':
                msg = "No CR on beginning"

            # print(init_pckt[17].to_bytes())
            if iPack[18].to_bytes(1, 'big') != b'\n':
                msg = "No NL on end"

            # print(len(init_pckt))
            if len(iPack) != 19:
                msg = "init packet wrong length"
            
            if msg != "":
                self.state = State.disconnected
                raise Exception(msg)

            self.handleInitPack(iPack)
            self.calibrate()
            self.removeBias()
            
            return 1
            # print("Init packet formatted correctly")
        except Exception as e:
            print("Init packet error: " + str(e))
            print(iPack)
            self.halt()
            return -1


    def handleInitPack(self, pack):
        # cleaned = pack.strip().decode('utf-8')
        self.num_modules = pack.count(b'2')
        self.channels = self.num_modules*8
        print(f'num_modules: {self.num_modules}')

    def stopStream(self):
        print('changing state')
        self.state = State.connected

    def stream(self):
        if(not self.state.streaming):
            return False
        
        # self.safe_serial_reset_buffers()
        time.sleep(1)
        self.safe_serial_write(b'b')
        time.sleep(1)
        # set up lsl
        name = "AxonEEG"
        type = "EEG"
        srate = 250
        info = StreamInfo(name, type, self.channels, srate, "float32", "myuid34234")
        outlet = StreamOutlet(info)
        incomingSize = 5+24*self.num_modules

        b_order = 6
        fs = 250.0  # sample rate, Hz
        low_cutoff = 15.0  # desired cutoff frequency of the filter, Hz
        high_cutoff = 1.0  # desired cutoff frequency of the filter, Hz
        notch_center = 60.0  # desired frequency to remove with notch filter, Hz
        counter = 0
        # with 1==1:
        while self.state==State.streaming:
            while True:
                if(self.ser.read()==b"\r"):
                    print("got a new line")
                    break
            #     break
            # while True:
            #     if self.safe_serial_read() == b"\r":
            #         break
            pckt_type_byte = self.ser.read(1).hex()
            pckt_type = int(bytearray.fromhex(pckt_type_byte).decode("utf-8"), 16)
            if pckt_type == PcktType.DATA.value:
                incoming = self.ser.read(incomingSize).hex()
                line = incoming[2:]
                sample_num = int.from_bytes(bytearray.fromhex(incoming[0:2]), byteorder='big')
                n = 6
                chunks = [line[i:i + n] for i in range(0, len(line), n)]
                    # if self.voltage_calib:
                rawSample = numpy.array([self.convertReadingVCal(chunks[i], self.c_factor[i]) for i in range(0, 8 * self.num_modules)])
                    # else:
                    #     rawSample = numpy.array([convertReading(chunks[i])/100 for i in range(0, 8 * num_modules)])
                sample = rawSample
            # for chan in range(0, len(rawSample)):
            # data = rawSample[:,chan] - np.mean(rawSample[:,chan])
            # y = butter_lowpass_filter(data, low_cutoff, fs, b_order)
            # y = butter_highpass_filter(y, high_cutoff, fs, b_order)
            # sample = iir_notch_filter(y, notch_center, fs)
                # print("sample", file=sys.stdout)
                # print(sample, file=sys.stdout)
                # print("sample")
            # print(sample)
                outlet.push_sample(sample.tolist())
        print('stopping...')
        self.safe_serial_write(b'c')
        # print(f'state is {self.state}')
        # if(self.state == State.closing):
        #     sys.exit()
        print(self.state)
        self.state = State.connected

    # Function to convert the hex readings to properly signed integers
    def convertReading(self, reading):
        reading = int(reading, 16)
        if reading >= int(0x800000):
            reading -= (int(0xFFFFFF) + 1)
        return reading

    # Function to convert the hex readings to voltage calibrated values
    def convertReadingVCal(self, reading, c_factor):
        reading = self.convertReading(reading)
        return reading * c_factor