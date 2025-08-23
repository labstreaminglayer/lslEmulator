from EmulatorCOM import EmulatorCOM
from AxonCOM import State
import serial.tools.list_ports as port_list
import sys
streamingStarted = False
emmy = EmulatorCOM()

print("connecting...")
emmy.connect("commock")

emmy.init()



while(True):
    if(not emmy.state==State.streaming):
        print("streaming")
        emmy.stream()
        streamingStarted = True