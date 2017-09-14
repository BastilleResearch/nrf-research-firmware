#!/usr/bin/python
# Modified rfcat_server to support Metasploit HWBridge

import re
import os
import sys
import cmd
import time
import json
import base64
import socket
import threading

from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from urlparse import parse_qs,urlparse
from lib import common, nrf24_reset

# Global Nic used for MSFHandler
radio = None
crc = False
address = None
last_errors = 0
starttime = 0
packets_sent = 0
last_sent = 0
username = None
password = None

class MSFHandler(BaseHTTPRequestHandler):
    def status(self):
        status = {}
        hw_version = "not suppoted"
        fw_version = "not supported"
        status["operational"] = 1 # Possibly connect this to ping?
        status["hw_specialty"] = { "rftransceiver": True }
        status["hw_capabilities"] = { "nrf24": True}
        status["last_10_errors"] = last_errors
        status["api_version"] = "0.0.2"
        status["fw_version"] = fw_version
        status["hw_version"] = hw_version
        return status

    def statistics(self):
        stats = {}
        stats["uptime"] = int(time.time()) - starttime
        stats["packet_stats"] = packets_sent
        stats["last_request"] = last_sent
        stats["voltage"] = "0.0v"
        return stats

    def datetime(self):
        return { "sytem_datetime": int(time.time()) }

    def timezone(self):
        return { "system_timezone": time.strftime("%Z") }

    def supported_idx(self):
        indexes = radio.supported_indexes()
        return { "indexes": indexes }  

    def reset(self):
        nrf24_reset.reset_radio(0)
        return { "status": "Resetting" }

    def set_freq(self, args):
        return self.not_supported()

    def get_modulations(self):
        mods = [ "2FSK" ]
        return mods

    def set_modulation(self, args):
        if not "mod" in args:
            return self.not_supported()
        modvalue = -1
        for modv, modstr in MODULATIONS.items():
            if modstr.split(' ')[0] == args["mod"][0]:
                modvalue = modv
        if modvalue == -1:
            return self.not_supported()
        # device can noly use 2FSK
        return { "success": True }

    # Fixed Len
    def make_packet_flen(self, args):
        return self.not_supported()

    # Variable Len
    def make_packet_vlen(self, args):
        return self.not_supported()

    # Modes supported:
    #  TX Mode is a Tone Test
    #  RX Mode varies based on active settings
    #    if an address is specified via set_sync_word then sniffer_mode is used
    #    if a CRC is set then promiscous_mode is used
    #    if neither specified then promiscous_mode_generic is used
    #  IDLE isn't currently supported
    def set_mode(self, args):
        if not "mode" in args:
            return self.not_supported()
        mode = args["mode"][0]
        if mode == "TX" or mode == "tx":
            radio.enter_tone_test_mode()
        elif mode == "RX" or mode == "rx":
            global crc
            global address
            if address:
                hex_address = [int(b, 16) for b in address.split(':')]
                radio.enter_sniffer_mode(self.serialize_address(hex_address))
            elif crc:
                radio.enter_promiscuous_mode()
            else:
                radio.enter_promiscuous_mode_generic()
        elif mode == "IDLE" or mode == "idle":
            return self.not_supported()
        else:
            return self.not_supported()
        return { "success": True }

    def enablePktCRC(self):
        global crc
        crc = True
        return { "success": True }

    def enableManchester(self):
        return self.not_supported()

    def set_channel(self, args):
        if not "channel" in args:
            return self.not_supported()
        radio.set_channel(int(args["channel"][0]))
        return { "success": True }

    def set_channel_bandwidth(self, args):
        return self.not_supported()

    def set_channel_spc(self, args):
        return self.not_supported()

    # Techncially we could support this via one of the sniffer modes
    # there are 3 possible options: 0=250k, 1=1M, 2=2M
    # This doesn't really fit the HWBridge API so for now we won't support it
    # This could be changed in the future if there is a desire to use it
    def set_baud_rate(self, args):
        return self.not_supported()

    def set_deviation(self, args):
        return self.not_supported()

    # The sync word is the target address.  When set this changes RX to use
    # a sniffer mode specific to that address
    # Unlike normal sync words 'word' here is a hex string ie: A7:31:FC:2D:66
    def set_sync_word(self, args):
        if not "word" in args:
            return self.not_supported()
        global address
        address = args["word"][0]
        return { "success": True}

    def set_sync_mode(self, args):
        return self.not_supported()

    def set_number_preamble(self, args):
        return self.not_supported()

    def set_maxpower(self):
        radio.enable_lna()
        return { "success": True }

    def set_power(self, args):
        return self.not_supported()

    # There are 3 ways to transmit
    # If we are using CRC then we will use ESB mode
    #   If in ESB mode and we don't request repeating we use the ACK method
    def rfxmit(self, args):
        repeat = 0
        offset = 0
        if not "data" in args:
            return self.not_supported()
        if "repeat" in args:
            repeat = int(args["repeat"][0])
        if "offset" in args:
            offset = int(args["offset"][0])
        data = base64.urlsafe_b64decode(args["data"][0])
        global crc
        global packets_sent
        global last_sent
        if crc:
            if repeat > 0:
                #debugstr = ':'.join('{:02X}'.format(x) for x in data)
                #debugstr = ':'.join('{%02X' % x for x in data)
                hex_chars = map(hex,map(ord,data))
                print("DEBUG: ({0}) DATA={1}".format(time.time() - last_sent, hex_chars))
                if radio.transmit_payload(data, 4, repeat):
                    packets_sent += 1
                    last_sent = time.time()
                    return { "success": True }
                return { "success": False }
            else:
                if radio.transmit_ack_payload(data):
                    packets_sent += 1
                    last_sent = time.time()
                    return { "success": True }
                return { "success": False }
        else:
            global address
            if address:
                hex_address = [int(b, 16) for b in address.split(':')]
                radio.transmit_payload_generic(data, self.serialize_address(address))
            else:
                radio.transmit_payload_generic(data)
        packets_sent += 1
        last_sent = time.time()
        return { "success": True } # Should do some checks here eventually

    def rfrecv(self, args):
        timeout=None
        blocksize=None
        # Note: Currently timeout is ignored as a parameter (done on init instead)
        if "timeout" in args:
            timeout = int(args["timeout"][0])
        try:
            data = radio.receive_payload()
        except:
            return {}
        address, payload = data[0:5], data[5:]
        return { "data": base64.urlsafe_b64encode(data), "timestamp": time.time() }
        

    def not_supported(self):
        return { "status": "not supported" }

    def serialize_address(self, a):
        return ''.join(chr(b) for b in a[::-1])

    def send(self, data, resp=200):
        self.send_response(resp)
        self.send_header('Content-type','application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data))
        return
        
    def do_AUTHHEAD(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm=\"NordicRF MSF Relay\"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write("Please Authenticate")

    def do_GET(self):
        if not password == None:
            if self.headers.getheader('Authorization') == None:
                print("Did not authenticate")
                self.do_AUTHHEAD()
                return
            if not self.headers.getheader('Authorization') == 'Basic '+base64.b64encode(username + ":" + password):
                print("Bad Authentication")
                self.do_AUTHHEAD()
                return
        # Note: A lot of methods are not supported by the Nordic chipset and are just here for API reference
        url = urlparse(self.path)
        args = parse_qs(url.query)
        if self.path=="/status":
            self.send(self.status())
        elif self.path=="/statistics":
            self.send(self.statistics())
        elif self.path=="/settings/datetime":
            self.send(self.datetime())
        elif self.path=="/settings/timezone":
            self.send(self.timezone())
        elif self.path=="/control/factory_reset":
            self.send(self.reset())
        elif self.path=="/rftransceiver/supported_idx":
            self.send(self.supported_idx())
        elif self.path.startswith("/rftransceiver/"):
            re_idx = re.compile("/rftransceiver/(\d+)/")
            m = re_idx.match(self.path)
            if m:
                idx = m.group(1)
                if self.path.find("/set_freq?") > -1:
                    self.send(self.set_freq(args))
                elif self.path.find("/get_modulations") > -1:
                    self.send(self.get_modulations())
                elif self.path.find("/set_modulation?") > -1:
                    self.send(self.set_modulation(args))
                elif self.path.find("/set_mode?") > -1:
                    self.send(self.set_mode(args))
                elif self.path.find("/make_packet_flen?") > -1:
                    self.send(self.make_packet_flen(args))
                elif self.path.find("/make_packet_vlen?") > -1:
                    self.send(self.make_packet_vlen(args))
                elif self.path.find("/enable_packet_crc") > -1:
                    self.send(self.enablePktCRC())
                elif self.path.find("/enable_manchester") > -1:
                    self.send(self.enableManchester())
                elif self.path.find("/set_channel?") > -1:
                    self.send(self.set_channel(args))
                elif self.path.find("/set_channel_bandwidth?") > -1:
                    self.send(self.set_channel_bandhwidth(args))
                elif self.path.find("/set_channel_spc") > -1:
                    self.send(self.set_channel_spc(args))
                elif self.path.find("/set_baud_rate?") > -1:
                    self.send(self.set_baud_rate(args))
                elif self.path.find("/set_deviation?") > -1:
                    self.send(self.set_deviation(args))
                elif self.path.find("/set_sync_word?") > -1:
                    self.send(self.set_sync_word(args))
                elif self.path.find("/set_sync_mode?") > -1:
                    self.send(self.set_sync_mode(args))
                elif self.path.find("/set_number_preamble?") > -1:
                    self.send(self.set_number_preamble(args))
                elif self.path.find("/set_maxpower") > -1:
                    self.send(self.set_maxpower())
                elif self.path.find("/set_power?") > -1:
                    self.send(self.set_power(args))
                elif self.path.find("/rfxmit") > -1:
                    self.send(self.rfxmit(args))
                elif self.path.find("/rfrecv") > -1:
                    self.send(self.rfrecv(args))
                else:
                    self.send(self.not_supported(), 404)
            else:
                self.send(self.not_supported(), 404)
        else:
            self.send(self.not_supported(), 404)
        return

class NRF24_MSFRelay(cmd.Cmd):
    intro = """
       nrf24 Metasploit Relay
"""

    def __init__(self, init_radio, ip='0.0.0.0', nicport=8080):
        cmd.Cmd.__init__(self)
        self.printable = True

        global radio
        radio = init_radio
        self._ip = ip
        self._nicport = nicport
        self._nicsock = None
        self._pause = False

        self.start()

    def start(self):
        self._go = True
        while self._go:
            # serve the NIC port
            try:
                buf = ''
                self._nicsock = HTTPServer((self._ip, self._nicport), MSFHandler)
                starttime = int(time.time())
                print("nrf24 MSFRelay running.")
                self._nicsock.serve_forever()
            except KeyboardInterrupt:
                self._nicsock.socket.close()
                nic.cleanup()
                self._go = False
            except:
                sys.excepthook(*sys.exc_info())



if __name__ == "__main__":

    common.init_args('./nrf24-msfrelay.py')
    common.parser.add_argument('-u', '--user', default="msf_relay", help='HTTP Username', type=str)
    common.parser.add_argument('-p', '--password', default="nrf24_relaypass", help='HTTP Password', type=str)
    common.parser.add_argument('-P', '--Port', default=8080, type=int)
    common.parser.add_argument('--noauth', default=False, action="store_true", help='Do not require authentication')
    common.parser.add_argument('--localonly', default=False, action="store_true", help='Listen on localhost only')
    common.parse_and_init()

    ifo = common.args

    username = ifo.user
    password = ifo.password
    ip = "0.0.0.0"
    nicport = ifo.Port
    if ifo.noauth:
         username = None
         password = None
    if ifo.localonly:
         host = "127.0.0.1"

    dongleserver = NRF24_MSFRelay(common.radio, ip, nicport)
    
import atexit
atexit.register(cleanupInteractiveAtExit)
