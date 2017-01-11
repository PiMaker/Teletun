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
print 'Connecting to telegram...'

receiver = Receiver(host="localhost", port=4458)
sender = Sender(host="localhost", port=4458)

# Retrieve contact list
contacts = {}

try:
    counter = 0
    for c in sender.dialog_list():
        counter += 1
        contacts[counter] = c
        print unicode(counter) + ': \t' + unicode(c['print_name'])
except ConnectionError:
    print 'Could not connect to telegram-cli. Start it by issuing "telegram-cli --json -P 4458" in a separate console.'
    exit(1)

# Ask user to choose contact
i = input('Telegram online, please enter contact to connect to (by number): ')

if i not in contacts:
    print 'Please enter a number in the above range!'
    exit(1)


# Print username
username = unicode(contacts[i]['print_name'])
print 'Connecting to partner: ' + username


# Create TUN device for network capture and injections
tun = TunTapDevice(name='teletun-device')

print tun.name + ' has been created, information follows:'


# Set IP address based on --server flag
if '--server' in sys.argv:
    tun.addr = '10.8.0.1'
    tun.dstaddr = '10.8.0.2'
else:
    tun.addr = '10.8.0.2'
    tun.dstaddr = '10.8.0.1'

tun.netmask = '255.255.255.0'
tun.mtu = 1500

print 'Address: ' + tun.addr
print 'Dest.-Address: ' + tun.dstaddr
print 'Netmask: ' + tun.netmask
print 'MTU: ' + str(tun.mtu)


# Start TUN device
tun.up()
up = True


# Helper function that can be executed in a thread
def main_loop_starter():
    pass
    receiver.start()
    # Start the receive loop
    receiver.message(main_loop())


@coroutine
def main_loop():
    global up
    try:
        while up:
            # Receive message from telegram, this includes ALL messages
            msg = (yield)
            # Check if it is an actual "message" message and if the sender is our peer
            if msg is not None and msg['event'] == unicode('message')\
                    and not msg['own'] and msg['sender']['name'] == username:
                try:
                    # Decode data and write it to the tunnel
                    data = base64.b64decode(msg.text)
                    tun.write(data)
                except:
                    print msg.text
    except:
        print 'Receiver stopped'


print 'TUN is up'


# Create the receive thread via our helper method
thread = threading.Thread(target=main_loop_starter)

try:

    # Start the thread for receiving
    print 'Connecting to peer...'
    thread.start()
    print 'Connected! Sending Invitation!'

    # Send the invitation message
    sender.msg(username, unicode('Hello, I would like to establish a Layer 3 Tunnel with you! -teletun'))

    while up:
        # Continually read from the tunnel and write data to telegram in base64
        # TODO: Telegram supports unicode, base64 can probably be replaced for something less overhead-inducing
        buf = tun.read(tun.mtu)
        sender.msg(username, unicode(base64.b64encode(buf)))

except:
    print 'Exiting...'

# Cleanup and stop application
up = False
tun.down()
receiver.stop()

print 'Bye bye!'

# Literally Overkill

current_process = psutil.Process()
os.kill(current_process.pid, signal.SIGKILL)
