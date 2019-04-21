#!/usr/bin/env python2

import time, logging, crcmod, struct
from lib import common
from protocols import *

# Parse command line arguments and initialize the radio
common.init_args('./nrf24-scanner.py')
common.parser.add_argument('-p', '--prefix', type=str, help='Promiscuous mode address prefix', default='')
common.parser.add_argument('-t', '--dwell', type=float, help='Dwell time per channel, in milliseconds', default='100')
common.parser.add_argument('-d', '--data_rate', type=str, help='Data rate (accepts [250K, 1M, 2M])', default='2M', choices=["250K", "1M", "2M"], metavar='RATE')
common.parser.add_argument('-f', '--family', required=True, type=Protocols, choices=list(Protocols), help='Protocol family')
common.parse_and_init()

# Initialize the target protocol
if common.args.family == Protocols.HS304:
  p = HS304()
else:
  raise Exception("Protocol does not support sniffer/scanner: %s" % common.args.family)

# Start device discovery
p.start_discovery()
while True:
  pass
