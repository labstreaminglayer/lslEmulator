from EmulatorCOM import EmulatorCOM
from AxonCOM import State
import serial.tools.list_ports as port_list
import sys
import os
os.environ["PYLSL_LIB"] = r"C:\\Users\\Arnaud Delorme\\Desktop\\lslEmulator\\liblsl-1.16.2-Win_amd64\\lib\\lsl.lib"
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