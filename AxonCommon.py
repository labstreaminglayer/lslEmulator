import subprocess
from enum import Enum
import sys
import os
from subprocess import Popen
from pathlib import Path
DETACHED_PROCESS = 0x00000008

if(sys.platform=="darwin"):
#     load libraries
    extraLibraries = ":/Applications/MATLAB/MATLAB_Runtime/R2023b/runtime/maci64:/Applications/MATLAB/MATLAB_Runtime/R2023b/sys/os/maci64:/Applications/MATLAB/MATLAB_Runtime/R2023b/bin/maci64:/Applications/MATLAB/MATLAB_Runtime/R2023b/extern/bin/maci64"
    libPath = os.environ.get('DYLD_LIBRARY_PATH')
    if(libPath):
        os.environ['DYLD_LIBRARY_PATH'] = libPath+extraLibraries
    else:
        os.environ['DYLD_LIBRARY_PATH'] = extraLibraries
from urllib.parse import unquote
import os
class State(Enum):
    disconnected = 0
    connected = 1
    streaming = 2
    stopping = 3
    error = 4
    closing = 5

class AxonCommon:
    nfblabProcess = None
    inputThreadAlive = True
    state: State = State.disconnected
    # Determine the log directory dynamically
    log_dir = Path.home() / ".axon_common_logs"  # Store logs in the user's home directory under a hidden folder
    log_dir.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists

    # Define log file paths
    pythonLogFile = open(log_dir / "pythonLog.txt", "w")
    pythonerrFile = open(log_dir / "pythonErr.txt", "w")
    def halt(self):
        pass
    def handleCommand(self, command, repSer):
        cleanCommand = command.replace('\r\n','').replace('\n', '')
        if(len(cleanCommand)>1):
            # connect or bad
            if("connect "in cleanCommand):
                if("connect ble" in cleanCommand):
                    # connect ble
                    connected = self.connect()
                else:
                    target = cleanCommand.split(' ')[1]
                    print('connecting...')
                    connected = self.connect(target)
                if connected!=None and len(connected)<8:
                    response = f"connect response: success"
                else:
                    response = f"connect response: {connected}"
                repSer.send(str.encode(response))
            elif ("state" in cleanCommand):
                repSer.send(str.encode(self.state))
            elif ("spawn nfb" in cleanCommand):
                words = cleanCommand.split(' ')
                if(sys.platform=="win32"):
                    commandHere = " ".join(words[2:])
                    self.nfblabProcess = Popen(
                        commandHere, shell=True, stdin=None, stdout=None, stderr=None,
                        close_fds=True, creationflags=subprocess.DETACHED_PROCESS,
                    )
                else:
                    commandHere = words[2:]
                    self.nfblabProcess = Popen(
                        commandHere, shell=False, stdin=None, stdout=None, stderr=None,
                        close_fds=True
                    )
                print('lab started')
                repSer.send(str.encode("lab process started"))
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
                 if self.init() == -1:
                     repSer.send(str.encode("init failed"))
                     sys.exit()
                 repSer.send(str.encode("init success"))
            if (cleanCommand == 'c'):
                print("killing...")
                # self.pythonerrFile.flush()
                # self.pythonLogFile.flush()
                # self.pythonerrFile.close()
                # self.pythonLogFile.close()
                if(self.nfblabProcess!=None):
                    self.nfblabProcess.kill()
                    print(f"killing lab")
                self.state = State.closing
                if(not self.state==State.streaming):
                    self.inputThreadAlive = False
                    self.halt()
                    sys.exit()
                self.state = State.closing
                while(self.state == State.closing):
                    # 
                    pass

                if(not self.state==State.streaming):
                    self.inputThreadAlive = False
                    sys.exit()
                repSer.send(str.encode("finished"))
            if(cleanCommand=='b'):
                print('streaming...')
                self.state = State.streaming
                repSer.send (str.encode(f"stream success"))
            # self.commands[cleanCommand](self)