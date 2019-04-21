## Presentation Clickers

I was in the mood for some RF reverse-engineering, so I ordered a few presentation clickers and had a bit of fun. 

This is a fork of [nrf-research-firmware](readme-original.md) (which I wrote a few years ago Bastille). I've added support for a few new transceivers/protocols, and included keystroke injection POCs for 10 common presentation clickers.

## History

- 2019-04-20 - released first batch


## Devices Vulnerable to Keystroke Injection

| Vendor | Model | Protocol | RFIC | Added |
|------- | ----- | -------- | ---- | ----- |
| AmazonBasics | [P-001](https://www.amazon.com/AmazonBasics-P-001-Wireless-Presenter/dp/B01FV0FAL2/) | [AmazonBasics P-001](#AmazonBasics-P-001) | nRF24 | 2019-04-20
| Canon | [PR100-R](https://www.amazon.com/gp/product/B01CEAYTGE/) | [Canon PR100-R](#Canon-PR100-R) | PL1167 | 2019-04-20 |
| Funpick | [Wireless Presenter](https://www.amazon.com/Funpick-Presenter-PowerPoint-Presentation-Red（Power＜1mW）/dp/B07L4K79HN/) | [HS304](#HS304) | HS304 | 2019-04-20 |
| AMERTEER | [Wireless Presenter](https://www.amazon.com/AMERTEER-Wireless-Presenter-Controller-Presentation/dp/B06XDD3KM3/) | [HS304](#HS304) | HS304 | 2019-04-20 |
| BEBONCOOL | [D100](https://www.amazon.com/BEBONCOOL-Wireless-Presenter-Presentation-PowerPoint/dp/B00WQFFZ9I/) | [HS304](#HS304) | HS304 | 2019-04-20 |
| ESYWEN | [Wireless Presenter](https://www.amazon.com/Wireless-Presenter-ESYWEN-Presentation-PowerPoint/dp/B07D7X7X2M/) | [HS304](#HS304) | HS304 | 2019-04-20 |
| Red Star Tech | [PR-819](https://www.amazon.com/Red-Star-Tec-Presentation-PR-819/dp/B015J5KB3G/) | [HS304](#HS304) | HS304 | 2019-04-20 |
| DinoFire | [D06-DF-US](https://www.amazon.com/DinoFire-Presenter-Hyperlink-PowerPoint-Presentation/dp/B01410YNAM/) | [HS304](#HS304) | HS304 | 2019-04-20 |

## Protocols

### AmazonBasics P-001

#### Overview

This is almost certainly a generic protocol, but I haven't looked at any of the sister devices yet (i.e. [this one](https://www.amazon.com/gp/product/B07D75459D/)). For the moment I am categorizing this as a distinct protocol, but that will likely change once I test the sister device(s).

The P-001 is based on the nRF24 RFIC family, and is functionally an unencrypted wireless keyboard, vulnerable to keystroke injection. 

#### PHY

The P-001 uses 2Mb/s nRF24 Enhanced Shockburst with 5-byte addresses, and channels 2402-2476.

#### Device Discovery

You can find the address of your P-001 using `nrf24-scanner.py`.

Pressing the right arrow should generate packets looking something like this:

```
[2019-04-20 12:59:13.908]  27   9  44:CB:66:A3:BE  00:00:00:00:00:00:00:00:01
[2019-04-20 12:59:13.909]  27   9  44:CB:66:A3:BE  00:00:00:00:00:00:00:00:01
[2019-04-20 12:59:13.999]  27   9  44:CB:66:A3:BE  00:00:4E:00:00:00:00:00:01
[2019-04-20 12:59:14.120]  27   9  44:CB:66:A3:BE  00:00:00:00:00:00:00:00:01
[2019-04-20 12:59:14.121]  27   9  44:CB:66:A3:BE  00:00:00:00:00:00:00:00:01
[2019-04-20 12:59:14.211]  27   9  44:CB:66:A3:BE  00:00:4E:00:00:00:00:00:01
```

#### Injection

Inject the test keystroke sequence into a specific AmazonBasics P-001 dongle (address `44:CB:66:A3:BE`):

```sudo ./tools/protocol-injector.py -l -f amazon -a 44:CB:66:A3:BE```


### Canon PR100-R

#### Overview

I'm not sure if this protocol is unique to the Canon PR100-R, but since it's the only device I've observed that speaks the protocol, I'm leaving it in its own bucket until the data suggests otherwise.

The PR100-R is based on the PL1167 RFIC, and an unknown MCU.

The PR100-R is functionally an unencrypted wireless keyboard, vulnerable to keystroke injection.

#### PHY

The PR100-R uses a 1Mb/s FSK protocol operating on 5Mhz-spaced channels between 2406 Mhz and 2481 MHz.

Packets are whitened, and protected by a 16-bit CRC. 

There don't appear to be ACKs sent back from the dongle, with the caveat that I've only reversed this protocol sufficient to demonstrate keystroke injection.

The protocol appears to take a frequency-agility approach to channel selection, and the dongle settles on a channel after the remote has transmitted on it for some number of packets. In practice, it is sufficient to transmit a few seconds of dummy packets before transmitting the keystroke packets.

#### Addressing

Based on the packet format, it's unclear if this protocol uses a fixed sync word, or a per-device address. I only looked at a single unit (due to the high price-point), so I wasn't able to fully vet the packet format.

The injection script works against my PR100-R, but may need to be modified for general use. **If you have another PR100-R and are able to validate this, please let me know!**

#### Injection

Inject the test keystroke sequence into a nearby Canon PR100-R dongle:

```sudo ./tools/protocol-injector.py -l -f canon```


### HS304

#### Overview

HS304 appears to be an application-specific RFIC for presentation clickers (or maybe wireless keyboards/mice). The name comes from the USB device string *HAS HS304*, and was the same for all devices in this set.

The RFIC was observed to be an unmarked SOP-16 package, with no apparent differences between vendors.

HS304-based devices are functionally unencrypted wireless keyboards, vulnerable to keystroke injection.

#### PHY

HS304 is a 1Mb/s FSK protocol operating on three channels in the 2.4GHz ISM band (2407, 2433, 2463). There don't appear to be ACKs sent from the dongle back to the presentation clicker, and packet delivery is ensured by transmitting each packet on each of the three channels.

In practice, reliable packet delivery can also be achieved by transmitting each packet multiple times on a single channel.

Packets are whitened, and protected by a 16-bit CRC. 

#### Addressing

There is no addressing or pairing scheme, so keystroke injection does not require device-discovery, however the lack of ACKs precludes active discovery of dongles.

#### Injection

Inject the test keystroke sequence into nearby HS304 dongles:

```sudo ./tools/protocol-injector.py -l -f hs304```

#### Sniffing

Receive and decode packets sent from nearby NS304 presentation clickers:

```sudo ./tools/protocol-scanner.py -l -f hs304```