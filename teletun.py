#!/usr/bin/env python3

# (C) Stefan Reiter 2017
# (C) Radomír Polách 2020

from pytun import TunTapDevice
from pytg import Telegram
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
import logging
import argparse
import time

# Init stats
sent = 0
received = 0

# Init status
up = False 

# Tun
tun = False
encrypted = False

# Arguments
args = False

def main():
    global sent, received, up, tun, encrypted, args;

# Process arguments
    parser = argparse.ArgumentParser(description='Teletun - IP over Telegram')
    parser.add_argument('peer_id', help='peer id (list for contact list)')
    parser.add_argument('-r', '--server', help='server', action='store_true')
    parser.add_argument('-e', '--encrypted', help='secret chat', action='store_true')
    parser.add_argument('-p', '--src', help='peer address', default='10.8.0.2')
    parser.add_argument('-s', '--dst', help='server address', default='10.8.0.1')
    parser.add_argument('-m', '--mask', help='mask', default='255.255.255.0')
    parser.add_argument('-n', '--mtu', help='MTU', default=1500)
    parser.add_argument('-H', '--host', help='Telegram host address', default='localhost')
    parser.add_argument('-P', '--port', help='Telegram port', default=4458)
    parser.add_argument('-a', '--auto', help='autoconfig from server', action='store_true')
    args = parser.parse_args()
    peer_id = None

# Connect to telegram
    print('Connecting to Telegram...', file=sys.stderr)
    receiver = Receiver(host=args.host, port=args.port)
    sender = Sender(host=args.host, port=args.port)

# Retrieve contact list

    try:
        contacts = [c for c in sender.dialog_list()]
        for i, user in enumerate(contacts):
            if args.peer_id == 'list':
                print('{:16s} {}'.format(str(user['peer_id']), str(user['print_name'])))
            elif str(user['peer_id']) == args.peer_id:
                peer_id = args.peer_id
                username = str(user['print_name']) 
        if args.peer_id == 'list':
            sys.exit(0)
    except ConnectionError:
        print('Could not connect to telegram-cli. Start it by issuing "telegram-cli --json -P 4458" in a separate console.', file=sys.stderr)
        sys.exit(1)

    if peer_id is None:
        print('Could not find peer_id in contact list.', file=sys.stderr)
        sys.exit(1)

    print('Connecting to partner: ' + username, file=sys.stderr)

# Helper function that can be executed in a thread
    def main_loop_starter():
        receiver.start()
        # Start the receive loop
        receiver.message(main_loop())

    @coroutine
    def main_loop():
        global args, received, tun, encrypted;
        while up:
            # Receive message from telegram, this includes ALL messages
            msg = (yield)
            # Check if it is an actual "message" message and if the sender is our peer
            if (
                msg is not None and
                msg.event == str('message') and
                not msg.own and
                str(msg.sender.peer_id) == peer_id
            ):
                print('Msg: ' + msg.text, file=sys.stderr)
                if msg.text[0] == '-' and msg.text[1] == '-':
                    if args.server:
                        if msg.text == '--encrypted':
                            print('Requested encyption for: ' + username, file=sys.stderr)
                            try:
                                sender.create_secret_chat(username)
                            except Exception:
                                pass
                            encrypted = True
                        elif msg.text == '--server':
                            command_line = '--src={} --dst={} --mask={} --mtu={:d}'.format(args.src, args.dst, args.mask, args.mtu)
                            print('Requested encyption for: ' + command_line, file=sys.stderr)
                            print('Sending configuration:' + command_line, file=sys.stderr)
                            sender.msg(username, str(command_line))
                    else:
                        print('Receiving configuration:' + data, file=sys.stderr)
                        args = parser.parse_args(sys.argv + data.split())
                        tun.down()
                        setup_tun()
                        tun.up()
                else:
                    # Decode data and write it to the tunnel
                    data = base64.b64decode(msg.text)
                    received += len(data)
                    tun.write(data)
                    #print('Packet written', file=sys.stderr)

    def setup_tun():
        if args.server:
            tun.addr = args.dst
            tun.dstaddr = args.src 
        else:
            tun.addr = args.src + ' '
            tun.dstaddr = args.dst 

        tun.netmask = args.mask
        tun.mtu = args.mtu

        print('\tSrc:  ' + tun.addr, file=sys.stderr)
        print('\tDst:  ' + tun.dstaddr, file=sys.stderr)
        print('\tMask: ' + tun.netmask, file=sys.stderr)
        print('\tMTU:  ' + str(tun.mtu), file=sys.stderr)


# Create TUN device for network capture and injections
    tun = TunTapDevice(name='teletun')

    print('Device ' + tun.name + ' has been created, information follows:', file=sys.stderr)

    if args.server or not args.auto:
# Set IP address based on --server header
        setup_tun()

# Start TUN device
    tun.up()
    up = True
        
    print('Device ' + tun.name + ' is up.', file=sys.stderr)

    if not args.server and args.encrypted:
        print('Requesting encyption for: ' + username, file=sys.stderr)
        sender.msg(username, '--encrypted')
        time.sleep(3)

# Create the receive thread via our helper method
    thread = threading.Thread(target=main_loop_starter)

# Start the thread for receiving
    print('Connecting...', file=sys.stderr)
    thread.start()
    
    if not args.server and args.auto:
        print('Waiting for configuration...', file=sys.stderr)
        command_line = '--server'
        sender.msg(username, str(command_line))
    
    while up:
        # Continually read from the tunnel and write data to telegram in base64
        # TODO: Telegram supports str, base64 can probably be replaced for something less overhead-inducing
        buf = tun.read(tun.mtu)
        data = base64.b64encode(buf)
        data = ''.join(map(chr, data))
        sent += len(data)
        if (not args.server and args.encrypted) or encrypted:
            sender.msg('!_' + username, data)
        elif not args.encrypted:
            sender.msg(username, data)

# Cleanup and stop application
    up = False
    tun.down()
    receiver.stop()

    print('Bytes sent via Telegram: ' + str(sent), file=sys.stderr)
    print('Bytes received via Telegram: ' + str(received), file=sys.stderr)
    print('Done.', file=sys.stderr)

# Literally Overkill
    current_process = psutil.Process()
    os.kill(current_process.pid, signal.SIGKILL)

if __name__== "__main__":
# Run main
    main()
