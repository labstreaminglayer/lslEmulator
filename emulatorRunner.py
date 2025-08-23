import sys
import os
import serial.tools.list_ports as port_list

# Set PYLSL_LIB environment variable BEFORE importing any modules that use pylsl
if sys.platform == "win32":
    os.environ["PYLSL_LIB"] = r"C:\\Users\\Arnaud Delorme\\Desktop\\lslEmulator\\liblsl-1.16.2-Win_amd64\\lib\\lsl.lib"
elif sys.platform == "darwin":
    os.environ["PYLSL_LIB"] = r"/Users/arno/Python/lslEmulator/liblsl-1.16.2-OSX_amd64/lib/liblsl.dylib"
else:
    print("Unsupported platform")
    exit()

# Now import modules that depend on pylsl
from EmulatorCOM import EmulatorCOM
from AxonCOM import State

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