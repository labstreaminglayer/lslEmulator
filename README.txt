Install
- create env: python -m venv .venv
- source .venv/bin/activate
- pip install -r requirements.txt
- pip install pyserial pylsl
- comment "from signal_processing" line in AxonCOM.py
- download the LSL lib release and uncompress https://github.com/sccn/liblsl/releases
- set env "export PYLSL_LIB="/Users/arno/Python/lslEmulator/liblsl-1.16.2-OSX_amd64/lib/liblsl.1.16.2.dylib" "
- run python emmulatorRunner.py

- change number of channels in lines 95 and 96 of EmulatorCOM.py
