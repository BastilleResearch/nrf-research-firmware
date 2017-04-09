#!/usr/bin/env python

import sys

from unifying import *

if len(sys.argv) < 2:
  print "Usage: sudo ./logitech-usb-backup.py [firmware-backup.bin] [infopage.bin]"
  sys.exit(1)

dongle = None

path = sys.argv[1]
with open(path, 'wb') as f:

  data = []

  # Instantiate the dongle
  dongle = unifying_dongle()

  for x in xrange(0x800):
    addr = 16 * x
    h = addr / 256
    l = addr & 255
    response = dongle.send_command(0x21, 0x09, 0x0200, 0x0000, "\x10" + chr(h) + chr(l) + "\x10\x00" + "\x00"*27)
    data += response[4:20]

  for value in data:
    f.write(chr(value))

path = sys.argv[2]
with open(path, 'wb') as f:

  data = []

  for x in xrange(0xfe0, 0x1000):
    addr = 16 * x
    h = addr / 256
    l = addr & 255
    response = dongle.send_command(0x21, 0x09, 0x0200, 0x0000, "\x10" + chr(h) + chr(l) + "\x10\x00" + "\x00"*27)
    data += response[4:20]

  for value in data:
    f.write(chr(value))

# restart dongle
response = dongle.send_command(0x21, 0x09, 0x0200, 0x0000, "\x70" + "\x00"*31)
