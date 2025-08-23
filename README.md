# An LSL emulator that just works

This emulator creates a stream of random data. It is useful for LSL testing or debugging purposes. Install on Windows os OSx. Then type

```
python emulatorRunner.py
```

It works!

```
2025-08-22 21:07:20.176 (   0.804s) [          1D5DF5]      netinterfaces.cpp:91    INFO| netif 'lo0' (status: 1, multicast: 32768, broadcast: 0)
2025-08-22 21:07:20.177 (   0.805s) [          1D5DF5]      netinterfaces.cpp:91    INFO| netif 'lo0' (status: 1, multicast: 32768, broadcast: 0)
2025-08-22 21:07:20.177 (   0.805s) [          1D5DF5]      netinterfaces.cpp:102   INFO| 	IPv4 addr: 7f000001
2025-08-22 21:07:20.177 (   0.805s) [          1D5DF5]      netinterfaces.cpp:91    INFO| netif 'lo0' (status: 1, multicast: 32768, broadcast: 0)
2025-08-22 21:07:20.177 (   0.805s) [          1D5DF5]      netinterfaces.cpp:105   INFO| 	IPv6 addr: ::1
2025-08-22 21:07:20.177 (   0.805s) [          1D5DF5]      netinterfaces.cpp:91    INFO| netif 'lo0' (status: 1, multicast: 32768, broadcast: 0)
2025-08-22 21:07:20.177 (   0.805s) [          1D5DF5]      netinterfaces.cpp:105   INFO| 	IPv6 addr: fe80::1%lo0
2025-08-22 21:07:20.177 (   0.805s) [          1D5DF5]      netinterfaces.cpp:91    INFO| netif 'gif0' (status: 0, multicast: 32768, broadcast: 0)
2025-08-22 21:07:20.177 (   0.805s) [          1D5DF5]      netinterfaces.cpp:91    INFO| netif 'stf0' (status: 0, multicast: 0, broadcast: 0)
2025-08-22 21:07:20.177 (   0.805s) [          1D5DF5]      netinterfaces.cpp:91    INFO| netif 'anpi1' (status: 1, multicast: 32768, broadcast: 2)
...
```

# Install for Windows and OSx
- create env: "python -m venv .venv"
- activate "source .venv/bin/activate" on OSx and ".\.venv\Scripts\Activate.bs1" on Windows
- "pip install -r requirements.txt"

# Install for other platforms
- download the LSL lib release and uncompress https://github.com/sccn/liblsl/releases
- change environment var in emulatorRunner.py

# Change the number of channels

Change the number of channels in lines 95 and 96 of EmulatorCOM.py.

# Credits
- Designed by Dylan Brown
- Packaged by Arnaud Delorme
