from protocol import Protocol
from collections import namedtuple
import time


class Injector(object):

  def __init__(self, protocol):

    self.protocol = protocol
    self.scan_codes = {
      " ": 0x2c,
      "-": 0x2d,
      "=": 0x2e,
      "[": 0x2f,
      "]": 0x30,
      "|": 0x31,
      ";": 0x33,
      "\"": 0x34,
      "`": 0x35,
      ",": 0x36,
      ".": 0x37,
      "/": 0x38,
    }

    self.scan_codes_shift = {
      "!": 0x1e,
      "@": 0x1f,
      "#": 0x20,
      "$": 0x21,
      "%": 0x22,
      "^": 0x23,
      "&": 0x24,
      "*": 0x25,
      "(": 0x26,
      ")": 0x27,
      "_": 0x2d,
      "+": 0x2e,
      "{": 0x2f,
      "}": 0x30,
      "\\": 0x31,
      ":": 0x33,
      "'": 0x34,
      "~": 0x35,
      "<": 0x36,
      ">": 0x37,
      "?": 0x38,
    }

  def test(self):
    for x in range(0xff):
      print("%04x"%x)
      self.protocol.send_hid_event(mouse_b=0x80, test=x)
      # self.protocol.send_hid_event(mouse_b=x)
      self.protocol.send_hid_event(mouse_b=0)

  def send_enter(self, shift=False, ctrl=False, win=False):
    self.protocol.send_hid_event(scan_code=0x28, shift=shift, ctrl=ctrl, win=win)
    self.protocol.send_hid_event(scan_code=0x00)

  def send_escape(self, shift=False, ctrl=False, win=False):
    self.protocol.send_hid_event(scan_code=0x29, shift=shift, ctrl=ctrl, win=win)
    self.protocol.send_hid_event(scan_code=0x00)

  def send_backspace(self, shift=False, ctrl=False, win=False):
    self.protocol.send_hid_event(scan_code=0x2a, shift=shift, ctrl=ctrl, win=win)
    self.protocol.send_hid_event(scan_code=0x00)

  def send_tab(self, shift=False, ctrl=False, win=False):
    self.protocol.send_hid_event(scan_code=0x2b, shift=shift, ctrl=ctrl, win=win)
    self.protocol.send_hid_event(scan_code=0x00)

  def send_capslock(self, shift=False, ctrl=False, win=False):
    self.protocol.send_hid_event(scan_code=0x39, shift=shift, ctrl=ctrl, win=win)
    self.protocol.send_hid_event(scan_code=0x00)

  def inject_string(self, string):

    for c in string:

      shift = False
      ctrl = False
      win = False

      char = ord(c.lower())
      if char >= ord("a") and char <= ord("z"):
        scan_code = char-ord("a")+0x04
        shift = c.isupper()
      elif char >= ord("0") and char <= ord("9"):
        scan_code = 0x27 if c == "0" else char-ord("1")+0x1e
      elif c in self.scan_codes:
        scan_code = self.scan_codes[c]
      elif c in self.scan_codes_shift:
        scan_code = self.scan_codes_shift[c]
        shift = True
      else:
        raise Exception("unsupported char %s" % c)

      self.protocol.send_hid_event(scan_code=scan_code, shift=shift)
      self.protocol.send_hid_event(scan_code=0x00, shift=shift)

  def start_injection(self):
    self.protocol.start_injection()
        

  def stop_injection(self):
    self.protocol.stop_injection()        