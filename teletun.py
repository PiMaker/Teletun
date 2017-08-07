#!/usr/bin/env python

# (C) Stefan Reiter 2017

from pytun import TunTapDevice
from pytg.sender import Sender
from pytg.receiver import Receiver
from pytg.utils import coroutine
from pytg.exceptions import ConnectionError
import base64
import threading
import sys
import psutil
import os
import signal


# Connect to telegram
print('Connecting to telegram...')

receiver = Receiver(host="localhost", port=4458)
sender = Sender(host="localhost", port=4458)

# Retrieve contact list

try:
    contacts = [c for c in sender.dialog_list()]
    for i, user in enumerate(contacts):
        print(unicode(i) + ': \t' + unicode(user['print_name']))
except ConnectionError:
    print('Could not connect to telegram-cli. Start it by issuing "telegram-cli --json -P 4458" in a separate console.')
    sys.exit(1)

# Ask user to choose contact
i = int(input('Telegram online, please enter contact to connect to (by number): '))

# Print username
try:
    username = unicode(contacts[i]['print_name'])
    peer_id = contacts[i]['peer_id']
    print('Connecting to partner: ' + username)
except IndexError:
    print('Please enter a number in the above range!')
    sys.exit(1)

# Create TUN device for network capture and injections
tun = TunTapDevice(name='teletun-device')

print(tun.name + ' has been created, information follows:')


# Set IP address based on --server flag
if '--server' in sys.argv:
    tun.addr = '10.8.0.1'
    tun.dstaddr = '10.8.0.2'
else:
    tun.addr = '10.8.0.2'
    tun.dstaddr = '10.8.0.1'

tun.netmask = '255.255.255.0'
tun.mtu = 1500

print('Address: ' + tun.addr)
print('Dest.-Address: ' + tun.dstaddr)
print('Netmask: ' + tun.netmask)
print('MTU: ' + str(tun.mtu))


# Start TUN device
tun.up()
up = True


# Init stats
sent = 0
received = 0


# Helper function that can be executed in a thread
def main_loop_starter():
    receiver.start()
    # Start the receive loop
    receiver.message(main_loop())


@coroutine
def main_loop():
    global up
    global received
    while up:
        # Receive message from telegram, this includes ALL messages
        msg = (yield)
        # Check if it is an actual "message" message and if the sender is our peer
        if (
            msg is not None and
            msg['event'] == unicode('message') and
            not msg['own'] and
            msg['sender']['peer_id'] == peer_id
        ):
            # Decode data and write it to the tunnel
            data = base64.b64decode(msg.text)
            received += len(data)
            tun.write(data)


print('TUN is up')


# Create the receive thread via our helper method
thread = threading.Thread(target=main_loop_starter)

# Start the thread for receiving
print('Connecting to peer...')
thread.start()
print('Connected! Sending Invitation!')

# Send the invitation message
sender.msg(username, unicode('Hello, I would like to establish a Layer 3 Tunnel with you! -teletun'))

while up:
    # Continually read from the tunnel and write data to telegram in base64
    # TODO: Telegram supports unicode, base64 can probably be replaced for something less overhead-inducing
    buf = tun.read(tun.mtu)
    data = base64.b64encode(buf)
    sent += len(data)
    sender.msg(username, unicode(data))

# Cleanup and stop application
up = False
tun.down()
receiver.stop()

print('Bytes sent via Telegram: ' + str(sent))
print('Bytes received via Telegram: ' + str(received))

print('~~ Bye bye! ~~')

# Literally Overkill

current_process = psutil.Process()
os.kill(current_process.pid, signal.SIGKILL)
