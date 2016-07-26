#!/usr/bin/env python

from unifying import *

# Compute CRC-CCITT over 1 byte
def crc_update(crc, data):
  crc ^= (data << 8)
  for x in range(8):
    if (crc & 0x8000) == 0x8000: crc = ((crc << 1) ^ 0x1021) & 0xFFFF
    else: crc <<= 1
  crc &= 0xFFFF
  return crc

# Make sure a firmware image path was passed in
if len(sys.argv) < 3:
  print "Usage: sudo ./logitech-usb-flash.py [firmware-image.bin] [firmware-image.ihx]"

# Compute the CRC of the firmware image
logging.info("Computing the CRC of the firmware image")
path = sys.argv[1]
with open(path, 'rb') as f:
  data = f.read()
crc = 0xFFFF
for x in range(len(data)):
  crc = crc_update(crc, ord(data[x]))

# Read in the firmware hex file
logging.info("Preparing USB payloads")
path = sys.argv[2]
with open(path) as f:
  lines = f.readlines()
  lines = [line.strip()[1:] for line in lines]
  lines = [line[2:6] + line[0:2] + line[8:-2] for line in lines]
  lines = ["20" + line + "0"*(62-len(line)) for line in lines]
  payloads = [line.decode('hex') for line in lines]
  payloads[0] = payloads[0][0:2] + chr((ord(payloads[0][2]) + 1)) + chr((ord(payloads[0][3]) - 1)) + payloads[0][5:]

# Add the firmware CRC
payloads.append('\x20\x67\xFE\x02' + struct.pack('!H', crc) + '\x00'*26)

# Instantiate the dongle
dongle = unifying_dongle()

# Init command (?)
logging.info("Initializing firmware update")
response = dongle.send_command(0x21, 0x09, 0x0200, 0x0000, "\x80" + "\x00"*31)

# # Clear the existing flash memory up to the size of the new firmware image
logging.info("Clearing existing flash memory up to boootloader")
for x in range(0, 0x70, 2):
  response = dongle.send_command(0x21, 0x09, 0x0200, 0x0000, "\x30" + chr(x) + "\x00\x01" + "\x00"*28)

# Send the data
logging.info("Transferring the new firmware")
for payload in payloads:
  response = dongle.send_command(0x21, 0x09, 0x0200, 0x0000, payload)
response = dongle.send_command(0x21, 0x09, 0x0200, 0x0000, payloads[0])

# Completed command (?)
logging.info("Mark firmware update as completed")
response = dongle.send_command(0x21, 0x09, 0x0200, 0x0000, "\x20\x00\x00\x01\x02" + "\x00"*27)

# Restart the dongle
logging.info("Restarting dongle into research firmware mode")
response = dongle.send_command(0x21, 0x09, 0x0200, 0x0000, "\x70" + "\x00"*31)
