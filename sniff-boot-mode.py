import glob
import serial
import sys
import time
# import os
import traceback
import json

usb_ttys = glob.glob("/dev/ttyUSB*")
if len(usb_ttys) == 0:
    print("Couldn't find any USB TTYs (/dev/ttyUSB*)")
    sys.exit(1)
elif len(usb_ttys) > 1:
    print("Found several USB TTYs, you need to tell me which to use:", usb_ttys)
    sys.exit(1)
else:
    port = usb_ttys[0]
    print("Found USB TTY: %s" % port)

ser = serial.Serial()
ser.port = port
ser.baudrate = 9600
ser.bytesize = 8
ser.parity = 'N'
ser.stopbits = 1
ser.timeout = 0.001 # read timeout?

# open the port
ser.open()
if not ser.is_open:
    print("Failed to open serial port")
    sys.exit(1)

buffer = []

last_data_time = time.time()

def wait_for_byte(ser):
    while True:
        data = ser.read(1)
        if data != b'':
            data = int.from_bytes(data, "big")
            print("<", hex(data))
            return data

def wait_for_bytes(ser, n_bytes):
    output = []
    for _ in range(n_bytes):
        this_byte = wait_for_byte(ser)
        output.append(this_byte)
    return output

# wait for 0x00 from flash development toolkit
# think basically setting up/syncing baud
# we could run at 9600, 4800, 2400, 1200 bauds and eventually it would send us what we think is a 0x00
for _ in range(3):
    data = wait_for_byte(ser)
    if data != 0x00:
        raise Exception("Unexpected data")

# reply 0x00 - bit rate automatic adjustment completed
ser.write([0x00])

# FDT sends 0x55 - automatic adjustment confirmation
data = wait_for_byte(ser)
if data != 0x55:
    raise Exception("Unexpected data")

# reply automatic adjustment confirmation successfully received
ser.write([0xe6])
# or could reply 0xff for error

"""
Detected generic boot device
Sending inquiry for getting line size
"""
# FDT sends 0x27
data = wait_for_byte(ser)
if data != 0x27:
    raise Exception("Unexpected data")

"""
what format to reply?
if you send 37,00 then it just times out and then sends next command anyway
"""
ser.write([0x37, 0x00])
"""
Error No 15005: 'COM7' read time out
Buffer size has been set to default (50214 bytes)
Sending selection of device command
"""

"""
The flash programmer sends the device select command (10h) to select the endian of data to be programmed in the user
area. The flash programmer uses the device code corresponding to the endian of the flash programmer in the device
codes that were stored by the support device inquiry command.
When the flash programmer receives a response (06h) after sending the device select command, it completes the endian
selection. When the flash programmer receives data other than the response (06h) after sending the device select
command, it resets the target MCU to abort.
10h (device select),
04h (size),
XXXXh (stored device code),
XXh (SUM)
"""
data = wait_for_bytes(ser, 7)
if data[0] != 0x10:
    raise Exception("Unexpected data")

# 06h (response to the device select command)
# 90h, 11h (checksum error)
# 90h, 21h (device code error)
ser.write([0x06])



"""
sends
0x11 0x1 0x0 0xee
Sending selection of clock mode
11h (clock mode selection)
01h (size)
00h (clock mode)
EEh (SUM)
"""
data = wait_for_bytes(ser, 4)
if data[0] != 0x11:
    raise Exception("Unexpected data")

"""
06h (response to the clock mode selection command)
91h, 11h (checksum error)
91h, 22h (clock mode error)
"""
ser.write([0x06])


"""
sends
0x3f 0x7 0x2 0x40 0x3 0xe8 0x2 0x4 0x2 0x85
3Fh (new bit rate selection)
07h (size)
3Ah, 98h (bit rate: 1.5 Mbps)
04h, B0h (input frequency)
02h (number of clock types)
08h (multiplication ratio 1)
04h (multiplication ratio 2)
26h (checksum)

reply:
06h (ACK)
BFh, 11h (checksum error)
BFh, 24h (bit rate selection error)
"""
data = wait_for_bytes(ser, 10)
if data[0] != 0x3f:
    raise Exception("Unexpected data")
print("got 0x3f change baud rate")
ser.write([0x06])
ser.flush()
time.sleep(0.020) # just making sure last reply sent before changing? needs this anyway
ser.baudrate = 57600

"""
Wait 25 ms
Change to 1.5 Mbps (whatever baud)
< 06h (confirmation data)

reply:
06h (response to the confirmation data)
BFh, 25h (input frequency error)
BFh, 26h (multiplication ratio error)
BFh, 27h (operati
"""
data = wait_for_byte(ser)
if data != 0x06:
    raise Exception("Unexpected data")
print("got 0x06 at new baud rate")
ser.write([0x06])



"""
sends 0x40
40h (programming/erasure state transition)

reply:
26h (response to the programming/erasure state transition command:
ID code protection disabled,
Transition to the wait state for the programming/erasure command)
16h (response to the programming/erasure state transition command:
ID code protection enabled,
Transition to the wait state for the ID code)
Store 00h in the ID code
protection status buffer
Store 01h in the ID code
protection status buffer
C0h, 51h (all-block erasure error)
"""
data = wait_for_byte(ser)
if data != 0x40:
    raise Exception("Unexpected data")
ser.write([0x26])


"""
sends 0x4f
4Fh (boot mode status inquiry)
5Fh, 02h, 3Fh, 00h, 60h
(response to the boot mode status inquiry command)
"""
data = wait_for_byte(ser)
if data != 0x4f:
    raise Exception("Unexpected data")
time.sleep(0.020)
ser.write([0x5f, 0x02, 0x3f, 0x00, 0x60])

# asks again, maybe the above reply is not right? does seem happy the second time though
data = wait_for_byte(ser)
if data != 0x4f:
    raise Exception("Unexpected data")
time.sleep(0.020)
ser.write([0x5f, 0x02, 0x3f, 0x00, 0x60])


"""
sends 0x4c
User boot MAT blank check Checks whether the contents of the user boot MAT
are blank
"""
data = wait_for_byte(ser)
if data != 0x4c:
    raise Exception("Unexpected data")
time.sleep(0.020)
ser.write([0x06])


"""  User MAT Blank Check """
data = wait_for_byte(ser)
if data != 0x4d:
    raise Exception("Unexpected data")
time.sleep(0.020)
ser.write([0x06])



# 4f again
data = wait_for_byte(ser)
if data != 0x4f:
    raise Exception("Unexpected data")
time.sleep(0.020)
ser.write([0x5f, 0x02, 0x3f, 0x00, 0x60])


"""
User MAT programming selection Transfers the user MAT programming program
"""
data = wait_for_byte(ser)
if data != 0x43:
    raise Exception("Unexpected data")
time.sleep(0.020)
ser.write([0x06])

print("done 0x43 -> 0x06")

# crashes here and windows app closes
# ran in compatibility mode for windows 7 and it works more



"""
)
Repeat until the user program is completely written
50h (program)
FFh, FXh, XXh, 00h (program address)
XXh, ... 256 bytes ... , XXh (program data)
XXh (SUM)
replies:
06h (response to the program command: ACK)
D0h, 11h (checksum error)
D0h, 2Ah (address error)
D0h, 53h (programming error)


first packet:

< 0x50
< 0x0
< 0x0
< 0x0
< 0x0
< 0x0
< 0x0
< 0xb
< 0x68
< 0xff
< 0xff
< 0xbf
< 0xa0
< 0x0
< 0x0
< 0xb
< 0x68
< 0xff
< 0xff
< 0xbf
< 0xa0
< 0x0
< 0x0
< 0xb
< 0x5a
< 0x0
< 0x0
< 0xb
< 0x5a
< 0x0
< 0x0
< 0xb
< 0x5a
< 0x0
< 0x0
< 0xb
< 0x5a
< 0x0
< 0x0
< 0xb
< 0x5a
< 0x0
< 0x0
< 0xb
< 0x5a
< 0x0
< 0x0
< 0xb
< 0x5a
< 0x0
< 0x0
< 0xb
< 0x38
< 0x0
< 0x0
< 0xb
< 0x5a
< 0x0
< 0x0
< 0xb
< 0x5a
< 0xff
< 0xff
< 0xff
< 0xff
< 0xff
< 0xff
< 0xff
< 0xff
< 0xdf
< 0x1
< 0x44
< 0x2b
< 0x0
< 0x9
< 0x0
< 0x0
< 0xff
< 0xff
< 0xbf
< 0xa0
< 0xdf
< 0x1
< 0x0
< 0xb
< 0x0
< 0x9
< 0x0
< 0x0
< 0xff
< 0xff
< 0xbf
< 0xa0
< 0xe5
< 0xf7
< 0x45
< 0x18
< 0x75
< 0xa
< 0x84
< 0x51
< 0xe3
< 0xff
< 0x43
< 0x18
< 0x62
< 0xc
< 0x73
< 0x7f
< 0x22
< 0x39
< 0x32
< 0x4c
< 0xe1
< 0x3c
< 0x62
< 0x2c
< 0x41
< 0x18
< 0x32
< 0x1c
< 0x25
< 0x21
< 0x0
< 0x9
< 0x0
< 0x9
< 0x0
< 0x9
< 0x0
< 0x9
< 0x0
< 0xb
< 0x78
< 0x4f

"""


"""
50h (program)
FFh, FFh, FFh, FFh (end of program)
B4h (SUM)

06h (response to the program command: ACK)
D0h, 11h (checksum error)
D0h, 2Ah (address error)
"""



# just loop reading
while True:
    wait_for_byte(ser)
