#!/usr/bin/env python

from socket import *
from select import select
from copy import copy
from datetime import datetime
import struct
import argparse
import os
import threading
from queue import Queue, Empty



def distance(a, b) :
    [x1,y1,z1] = a  # first coordinates
    [x2,y2,z2] = b  # second coordinates

    return (((x2-x1)**2)+((y2-y1)**2)+((z2-z1)**2))**(1/2)


class Handshake:
    fmt = '<100s100sII100s100s'
    size = struct.calcsize(fmt)

    def __init__(self, t):
        carName, driverName, self.identifier, self.version, trackName, trackConfig = t

        self.carName, self.driverName, self.trackName, self.trackConfig = map(
            lambda s: s.decode('utf-16', errors='ignore').split('%')[0] ,
            [carName, driverName, trackName, trackConfig]
        )

    @classmethod
    def fromData(cls, d):
        return cls(struct.unpack(Handshake.fmt, d))
        

    def __str__(self):
        return '{self.carName}, {self.driverName}, {self.trackName}, {self.trackConfig}'.format(self=self)


class Update:
    fmt = '<8x2f24x4I5fI236x3f'
    size = struct.calcsize(fmt)

    def __init__(self, t):
        self.speed_Kmh, self.speed_Mph, \
        self.lapTime, self.lastLap, self.bestLap, self.lapCount, \
        self.gas, self.brake, self.clutch, self.engineRPM, self.steer, \
        self.gear, self.x, self.y, self.z = t

    @classmethod
    def fromData(cls, d):
        return cls(struct.unpack(Update.fmt, d))

    def __str__(self):
        return '{self.speed_Kmh}, {self.gas}, {self.brake}, {self.engineRPM}, {self.x}, {self.y}, {self.z}'.format(self=self)

    def coords(self):
        return [self.x, self.y, self.z]


class ACListener(threading.Thread):

    def __init__(self, addr = '127.0.0.1', port=9996):
        super(ACListener,self).__init__()
        self.addr = addr
        self.port = port
        self.socket = socket(AF_INET,SOCK_DGRAM)
        self.socket.setblocking(0)
        self.connected = False
        self.event = None
        self.updates = Queue()

    def run(self):

        self.running = True

        self.dismiss()

        while self.running and not self.event:
            self.event = self.handshake()

        if self.event:
            print('connected')
            print(self.event)

            self.startUpdate()

            while self.running:
                self.nextUpdate()

        self.dismiss()
        self.close()

    def stop(self):
        self.running = False

    def recv(self, size):
        chunks = []
        bytes_recv = 0

        ready = select([self.socket], [], [], 2)
        if ready[0]:

            while bytes_recv < size:
                chunk = self.socket.recv(size - bytes_recv)
                if chunk == b'':
                    raise RuntimeError("socket connection broken")

                chunks.append(chunk)
                bytes_recv = bytes_recv + len(chunk)

            return b''.join(chunks)

    def handshake(self):
        print('sending handshake to {self.addr}:{self.port}'.format(self=self))
        pkt = struct.pack('iii',1,1,0)
        self.socket.sendto(pkt, (self.addr, self.port))
        h = self.recv(Handshake.size)
        if h:
            return Handshake.fromData(h)

    def startUpdate(self):
        pkt = struct.pack('iii',1,1,1)
        self.socket.sendto(pkt, (self.addr, self.port))

    def nextUpdate(self):
        u = self.recv(Update.size)
        if u:
            self.updates.put(Update.fromData(u), block=False)

    def dismiss(self):
        pkt = struct.pack('iii',1,1,3)
        self.socket.sendto(pkt, (self.addr, self.port))

    def close(self):
        self.dismiss()
        self.socket.close()

class Logger:

    def __init__(self, logattr, event):
        self.event = event
        self.logattr = logattr
        self.isodate = datetime.now().isoformat().replace(':', '').replace('-','')
        self.f = None

    def newlap(self, update):
        if self.f:
            self.f.close()

        fname = 'out/' + '_'.join([
                self.event.driverName,
                self.event.carName,
                self.event.trackName,
                self.event.trackConfig,
                self.isodate,
                str(update.lapCount)
            ]) + '.txt'

        self.f = open(fname.replace(' ', '_'), mode='w', buffering=1)
        self.f.write('\t'.join(logattr) + '\n')
        self.update(update)

    def update(self, update):
        if self.f:
            out = map(lambda a: str(getattr(update, a)), self.logattr)
            self.f.write('\t'.join(out) + '\n')

    def close(self):
        if self.f:
            self.f.close()

if __name__ == '__main__':

    logattr = ['lapTime', 'speed_Mph', 'gas', 'brake', 'steer', 'gear', 'x', 'y', 'z']
    os.makedirs('out', exist_ok=True)
    parser = argparse.ArgumentParser(description='Assetto Corsa Telemetry Logger')
    parser.add_argument('host', nargs='?', default='127.0.0.1',
                    help='host IP address running AC')
    parser.add_argument('port', nargs='?', type=int, default=9996,
                help='UDP port AC is listening on')     

    args = parser.parse_args()

    acl = ACListener(args.host, args.port)
    acl.start()

    logger = Logger(logattr, acl.event)

    lastUpdate = None
    finished = False

    while acl.isAlive() and not finished:

        try:

            update = acl.updates.get(timeout=1) # to allow windows to use CTRL+C

            if not update:
                continue

            if not lastUpdate:
                logger.newlap(update)
                lastUpdate = copy(update)
            elif lastUpdate.lapCount != update.lapCount:
                logger.newlap(update)
                lastUpdate = copy(update)
                print('lapCount: {lapCount}, lapTime: {lastLap}'.format(
                    lapCount=update.lapCount, lastLap=update.lastLap/1000)
                )
            elif distance(lastUpdate.coords(), update.coords()) > 1.0:
                logger.update(update)
                lastUpdate = copy(update)

        except Empty:
            pass

        except KeyboardInterrupt:
            print('stopping')
            finished = True

    logger.close()
    acl.stop()
    acl.join()
