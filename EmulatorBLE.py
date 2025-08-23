from AxonCommon import AxonCommon, State
from collections import deque
import asyncio
import threading
import numpy as np
import logging
import random
logger= logging.getLogger(__name__)
from dataclasses import dataclass
import time
from typing import List


class MockClient:
    def __init__(self, data_size):
        self.services = {
            "UART_SERVICE_UUID": MockService(),
            "get_service": MockService()
        }
        self._backend = MockBackend()
        self.mtu_size = 247
        self.initialization_sent = False # Init flag tracker
        self.stream_data_size = data_size
        self.should_wait = False
    def set_wait(self, wait):
        self.should_wait = wait

    async def start_notify(self, char_uuid, callback):
        await asyncio.sleep(1)
        msg = b""
        if self.should_wait:
            await asyncio.sleep(.1)
        elif not self.initialization_sent:
            print("Sending init packet.")
            msg = b"\r"+ b"1"*16 +b"2" + b"\n"
            self.initialization_sent = True
        else:
            await asyncio.sleep(1)
            msg = random.randbytes(self.stream_data_size)
        callback(char_uuid, bytearray(msg))

class MockCharacteristic:
	max_write_without_response_size = 20

class MockService:
	def get_service(self, uuid):
		return self
	def get_characteristic(self, uuid):
		return MockCharacteristic()

class MockBackend:
	def __init__(self):
		self.__class__.__name__ = "BleakClientBlueZDBus"
	async def _acquire_mtu(self):
		await asyncio.sleep(.1)

@dataclass
class MockDevices:
	address: str
	details: str
	name: str
	def __init__(self, address="", details="", name=""):
		address_bytes = np.random.bytes(6)
		adv_mock = f"<_bleak_winrt_Windows_Devices_Bluetooth_Advertisement.BluetoothLEAdvertisementReceivedEventArgs object at 0x{np.random.randint(0x100000, 0xFFFFFF):X}>"
		scan_mock = f"<_bleak_winrt_Windows_Devices_Bluetooth_Advertisement.BluetoothLEAdvertisementReceivedEventArgs object at 0x{np.random.randint(0x100000, 0xFFFFFF):X}>"
		details_temp = f"_RawAdvData(adv={adv_mock}, scan={scan_mock})"
		name_temp = f"Device{np.random.randint(1, 100)}"
		self.address = ":".join(f"{b:02X}" for b in address_bytes) if not address else address
		self.details = details_temp if not details else details
		self.name = name_temp if not name else name

	def generate(self, address="", details="", name="", number=10) -> "MockDevices":
		return [MockDevices(address, details, name) for i in range(number if number > 0 else 10)]
	def __str__(self):
		return f"{self.address}: {self.name}"
	def __repr__(self) -> str:
		return f"{self.__class__.__name__}({self.address}, {self.name})"

class MockBci:
    client: MockClient
    currentCommand = ""
    def __init__(self, stream_deque=deque()):
        self.UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E".lower()
        self.UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E".lower()
        self.UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E".lower()

        self.found_bci = None

        # 0 - Not running
        # 1 - Scanning
        # 2 - Running
        self.bci_state = 0
        self.bci_ble_thread = None

        # 0 - Not streaming
        # 1 - Ready to stream
        # 2 - Streaming
        self.stream_state = 0
        self.finished = 0

        self.num_modules = 0
        self.stream_deque = stream_deque

        self.tx_buff_len = 240

        # Packet transfer debugging
        self.pckts_rec = 0
        self.pckts_full = 0
        self.pckts_short = 0
        # If samples are set to zero, then it doesn't run the limited sample test.
        # Otherwise, it will run it for a set number of samples.
        self.samples = 0
        self.frame_times = np.empty(self.samples, dtype='float')
        self.client = MockClient(self.tx_buff_len)

    async def discover_bci(self):
        wait_time = 2
        bci_signatures = ["NTL-AXON-", "NTL-BCI-02"]
        devices_list = [MockDevices("","","NTL-AXON-BoardNo42")]
        for device in devices_list:
            print("-"*30)
            print(f"Device: {device}")
            print(f"Address: {device.address}")
            res = device.details
            print(f"Details: {res}")
            print(f"Name: {device.name}")
        devices_list = [dev for dev in devices_list if(any(ele in dev.name for ele in bci_signatures))]
        print(f"New device list: {devices_list}")
        if not devices_list:
            raise Exception("Devices detected, but not NTL AXON boards")
        return devices_list[0]

    def handle_rx(self, _: any, data: bytearray):
        print(f"Received: {data.hex()}")
        if self.get_stream_state() == 0:
            logger.info(f"Mode {self.get_stream_state()}, Received: {data.hex()}")
            try:
                if data[0].to_bytes(1, 'big') != b'\r':
                    raise Exception("No CR on beginning")
                if data[1].to_bytes(1, 'big') != b'1':
                    raise Exception("Not INIT packet")
                if data[18].to_bytes(1, 'big') != b'\n':
                    raise Exception("No NL at end")
                if len(data) != 19:
                    raise Exception("Init packet wrong length")
                logger.info("Init packet formatted correctly")
            except Exception as e:
                logger.error("Init packet error: " + str(e))
                self.num_modules = data[2:].count(b'2')
                self.set_stream_state(1)
                self.client.initialization_sent = True
        elif self.get_stream_state() == 2:
            self.pckts_rec += 1
            if self.samples > 0 and self.pckts_rec < self.samples:
                self.frame_times[self.pckts_rec] = time.time()
            if np.shape(data)[0] != self.tx_buff_len:
                logger.error(f"Received packet of incorrect length: {np.shape(data)[0]}")
                dpckt = np.array(data, dtype="B")
                print(dpckt)
                self.pckts_short += 1
            else:
                self.pckts_full += 1
                dpckt = np.array(data, dtype="B")
            if self.pckts_rec % 250 == 0:
                print(dpckt)
            if (self.pckts_rec >= self.samples) and self.samples > 0:
            # debugging purposes
                pass
        else:
            logger.info(f"Mode {self.get_stream_state()}, Received: {data.hex()}")

    async def connect_and_stream(self):
        wait_time = 10
        try:
            loop = asyncio.get_running_loop()
            nus = self.client.services.get("UART_SERVICE_UUID")
            rx_char = nus.get_characteristic("UART_RX_CHAR_UUID")
            try:
                await self.client.start_notify("UART_TX_CHAR_UUID", self.handle_rx)
            except Exception  as e:
                logger.error("TX notify failed", str(e))
            if self.client._backend.__class__.__name__ == "BleakClientBlueZDBus":
                await self.client._backend._acquire_mtu()

            print("MTU:" ,self.client.mtu_size)
            print("awaiting commands...")
            while self.bci_state ==2:
                if(self.currentCommand==""):
                    time.sleep(0.3)
                    break
                data = self.currentCommand
                print(f"Command {data}")
                
                if data == b"p":
                    num_mod = await self.setup_stream(self.client)
                    self.client.initialization_sent = True
                    if num_mod > 0:
                        self.num_modules = num_mod
                elif data == b"b":
                    await self.start_stream(self.client)
                elif data == b'c': 
                    await self.stop_stream(self.client)
                elif data == b'h':
                    await self.pause_stream(self.client)
                elif data == b'f':
                    await self.stop_stream(self.client)
                    # Debugging to print out number of packets received
                    print(f"Total packets received: {self.pckts_rec}")
                    print(f"Full packets received: {self.pckts_full}")
                    print(f"Short packets received: {self.pckts_short}")
                    print(f"Percentage of full packets: {(self.pckts_full/self.pckts_rec)*100}%")
                    print(f"Percentage of short packets: {(self.pckts_short/self.pckts_rec)*100}%")

                    self.set_finished(1)
                    logger.info("Stopping BCI BLE client")
                    break
                else:
                    logger.error(f"Command \"{data}\" invalid.")
                # self.handle_rx("", pack)
                self.currentCommand = ""
        except Exception as e:
            logger.error(f"Client exception {e}")
            wait_time = 1
        finally:
            await asyncio.sleep(wait_time)
        
   # Connection management
    async def run(self):
        try:
            while True:
                if self.bci_state == 0:
                    device = None
                if self.bci_state == 1:
                    logger.info("Scanning begun")
                    device = await self.discover_bci()
                if device and self.bci_state == 1:
                    logger.info(f"Found NTL BCI: {device}")
                    self.bci_state = 2
                    self.found_bci = device
                    logger.info("Running...")
                if self.bci_state == 2:
                    await self.connect_and_stream()
                if self.bci_state == 0:
                    break
        except Exception as e:
            logging.error(f"Unknown exception thrown {e}")
    
    # Thread Managers
    def start(self):
        self.bci_state = 1
        self.bci_ble_thread = threading.Thread(target=lambda: asyncio.run(self.run()), daemon=True)
        self.bci_ble_thread.start()

    def stop(self):
        self.bci_state = 0
    # Stream State Managers
    
    def get_stream_state(self):
        return self.stream_state

    def set_stream_state(self, state_val):
        self.stream_state = state_val

    async def setup_stream(self, client):
        msg = b"p"
        logger.info(f"Sent: {msg} init packet command")
        while True:
            if self.get_stream_state() == 1:
                logger.info(f"Ready to stream, {self.num_modules} modules connected")
                break
            await asyncio.sleep(0.2)
        return 1

    async def start_stream(self, client):
        if self.get_stream_state() == 1:
            msg = b"b"
            self.set_stream_state(2)
            logger.info(f"Sent: {msg} start command")
            self.client.set_wait(False)
            await asyncio.sleep(1)
            return 1
        else:
            logger.error(f"Stream cannot be started, currently in mode {self.get_stream_state()}")
            return 0  

    async def stop_stream(self, client):
        msg =  b"c"
        await asyncio.sleep(1)
        self.set_stream_state(0)
        self.client.set_wait(True)
        logger.info(f"Sent: {msg} stop command")
        return 1
    
    async def pause_stream(self, client):
        if self.get_stream_state() == 2:
            msg =  b"h"
            self.set_stream_state(1)
            logger.info(f"Sent: {msg} pause command")
            self.client.set_wait(True)
            await asyncio.sleep(1)
            return 1
        else:
            logger.error(f"Stream cannot be paused, currently in mode {self.get_stream_state()}")
            return 0
        
class EmulatorBLE(AxonCommon):
    # state:State = State.
    num_modules = 0
    inputThreadAlive = True
    output_stream = deque()
    bci = MockBci()

    def connect(self):
        self.bci.start()
        self.state = State.connected
        return "successful"
    def init(self):
        self.bci.currentCommand = b"p"

    def stream(self):
        self.bci.currentCommand = b"b"
        self.state = State.streaming

    def halt(self):
        self.bci.currentCommand = b"c"
        self.state = State.closing

    def stopStream(self):
        self.bci.currentCommand = b"h"
        self.state = State.connected
