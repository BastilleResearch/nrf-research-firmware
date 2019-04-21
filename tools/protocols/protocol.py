from threading import Thread
from enum import Enum
from lib import common


class Protocol(object):

  # Constructor
  def __init__(self, name):
    self.name = name
    self.cancel = False
    self.configure_radio()


  # Start device discovery loop
  def start_discovery(self):
    self.thread = Thread(target=self.discovery_loop, args=(self.cancel,))
    self.thread.daemon = True
    self.thread.start()


  # Stop device discovery loop
  def stop_discovery(self):
    self.cancel = True
    self.thread.join()


  # Configure the radio
  def configure_radio(self):
    raise NotImplemented()


  # Discovery loop
  def discovery_loop(self, cancel):
    raise NotImplemented()


  # Send a HID event
  def send_hid_event(self, scan_code, shift, ctrl, win):
    raise NotImplemented()


  # Enter injection mode
  def start_injection(self):
    raise NotImplemented()


  # Leave injection mode
  def stop_injection(self):
    raise NotImplemented()