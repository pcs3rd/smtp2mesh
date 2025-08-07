# Copyright 2014-2021 The aiosmtpd Developers
# SPDX-License-Identifier: Apache-2.0


import asyncio
import logging
import meshtastic.tcp_interface
import time
import configparser
import re
from concurrent.futures import ThreadPoolExecutor


from aiosmtpd.controller import Controller

config = configparser.ConfigParser() 
config_file = "config.ini"

try:
    config.read(config_file, encoding='utf-8')
except Exception as e:
    print(f"System: Error reading config file: {e}")

if config.sections() == []:
    print(f"System: Error reading config file: {config_file} is empty or does not exist.")
    config['general'] = {'msgSize': '160'}
    config['interface'] = {'hostname': 'meshtasticd'}
    config['smtp'] = {'domain': '@meshtastic.local', 'port': '25', 'bind':'localhost'}
    config.write(open(config_file, 'w'))
    print (f"System: Config file created at {config_file}.")
# Get config
try:
    smtpPort = config['general'].getint('msgSize', '160')
    mesh = config['interface'].get('hostname', 'meshtasticd')
    interface_enabled = True # gotta have at least one interface
    domain = config['smtp'].get('domain', '')
    smtpPort = config['smtp'].getint('port', '25')
    smtpIface = config['smtp'].get('bind', '0.0.0.0')
    msgSize = config['general'].getint('msgSize', '160')

    print(f"System:Starting smtp server at {smtpIface}:{smtpPort}")
except Exception as e:
    print (f"System: Failed to start configure ({e})!")

# Init meshtastic api
try:
    interface = meshtastic.tcp_interface.TCPInterface(mesh)
except Exception as e: 
    print (f"System: Failed to start meshtastic client ({e})!")

def send_message(node, message, msgSize):
    print(message)
    #chunks = [message[i:i+msgSize] for i in range(0, len(message), msgSize)]
    for chunk in [message[i:i+msgSize] for i in range(0, len(message), msgSize)]:
        print(f"System: Send Message: {chunk}")
        interface.sendText(
             text=chunk,
            destinationId=node,
            wantAck=True,
            wantResponse=True
        )
        return "250 OK"
    


class ExampleHandler:
    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        if not address.endswith(domain):
            return '550 not relaying to that domain'
        envelope.rcpt_tos.append(address)
        return '250 OK'

    async def handle_DATA(self, server, session, envelope):
        print('Inbound mail for node %s' % str(envelope.rcpt_tos[0]).split('@')[0])
        await asyncio.sleep(1)  
        with ThreadPoolExecutor(max_workers=2) as executor:
            send = executor.submit(send_message(str(envelope.rcpt_tos[0]).split('@')[0], str(envelope.content.decode('utf8', errors='replace')),  msgSize))
            #results = [send.result()]
        return '250 Message accepted for delivery'

async def amain(loop):
    cont = Controller(ExampleHandler(), hostname=smtpIface, port=smtpPort)
    cont.start()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(amain(loop=loop))  # type: ignore[unused-awaitable]
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("User abort indicated")