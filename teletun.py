#!/usr/bin/env python

from pytun import TunTapDevice
from pytg.sender import Sender
from pytg.receiver import Receiver
from pytg.utils import coroutine
import base64
import threading
import sys
import traceback
import os
import signal
import psutil


print 'Connecting to telegram...'

receiver = Receiver(host="localhost", port=4458)
sender = Sender(host="localhost", port=4458)

contacts = {}

counter = 0
for c in sender.dialog_list():
    counter += 1
    contacts[counter] = c
    print unicode(counter) + ': \t' + unicode(c['print_name'])

i = input('Telegram online, please enter contact to connect to (by number): ')

if i not in contacts:
    print 'Please enter a number in the above range!'
    exit(1)


username = unicode(contacts[i]['print_name'])
print 'Connecting to partner: ' + username


tun = TunTapDevice(name='teletun-device')

print tun.name + ' has been created, information follows:'


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

tun.up()
up = True


def main_loop_starter():
    pass
    receiver.start()
    receiver.message(main_loop())


@coroutine
def main_loop():
    global up
    try:
        while up:
            msg = (yield)
            if msg is not None and msg['event'] == unicode('message') and not msg['own']:
                try:
                    data = base64.b64decode(msg.text)
                    tun.write(data)
                except:
                    print msg.text
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        print ''.join('!! ' + line for line in lines)
        print 'Receiver stopped'


print 'TUN is up'


thread = threading.Thread(target=main_loop_starter)

try:

    print 'Connecting to peer...'
    thread.start()
    print 'Connected! Sending Invitation!'

    sender.msg(username, unicode('Hello, I would like to establish a Layer 3 Tunnel with you! -teletun'))

    while True:
        buf = tun.read(tun.mtu)
        sender.msg(username, unicode(base64.b64encode(buf)))

except:
    exc_type, exc_value, exc_traceback = sys.exc_info()
    lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    print ''.join('!! ' + line for line in lines)
    print 'Exiting...'

up = False
tun.down()

receiver.stop()

print 'Bye bye!'


# Literally Overkill

current_process = psutil.Process()
children = current_process.children(recursive=True)
for child in children:
    os.kill(child.pid, signal.SIGKILL)

children = current_process.children(recursive=True)
for child in children:
    os.kill(child.pid, signal.SIGKILL)

os.kill(current_process.pid, signal.SIGKILL)
