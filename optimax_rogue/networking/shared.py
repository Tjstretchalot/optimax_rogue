"""Shared networking components (ie. networking protocol)
"""
import socket
try:
    from queue import SimpleQueue as Queue
except:
    from queue import Queue as Queue

import io
import typing
import traceback
from collections import deque

import optimax_rogue.networking.packets as packets
import optimax_rogue.networking.serializer as ser

BLOCK_SIZE = 4096

class Connection:
    """Describes a connection either from the server to some client or from the client
    to the server

    Attributes:
        connection (socket.socket): how we communicate with the other entity
        address (str): where the entity connected from / where we connected to

        send_queue (queue[bytes]): the packets that we need to send
        rec_queue (queue[Packet]): the packets that they have sent us

        curr_send_packet (optional BytesIO): if we are currently trying to send a message
            to the client, this is the serialized message we are trying to send (that has
            already been removed from the send_queue)
        curr_rec (deque[bytes]): the things that we have in memory received
    """
    def __init__(self, connection: socket.socket, address: str) -> None:
        self.connection = connection
        self.address = address

        self.send_queue = Queue()
        self.rec_queue = Queue()

        self.curr_send_packet: io.BytesIO = None
        self.curr_rec = deque()

    def disconnected(self):
        """Returns True if the connection is dead for whatever reason, False otherwise"""
        return self.connection is None

    def update(self):
        """Handles sending and receiving packets in a non-blocking way. Must be called very
        regularly for send() and receive() to actually do anything
        """
        if self.disconnected():
            return

        try:
            self._handle_send()
            self._handle_rec()
        except BlockingIOError:
            pass
        except OSError:
            self.connection = None
            print(f'[networking.shared] connection lost')
            traceback.print_exc()


    def _handle_send(self):
        if self.curr_send_packet is None:
            if self.send_queue.empty():
                return
            packet_serd = self.send_queue.get_nowait()
            self.curr_send_packet = io.BytesIO()
            self.curr_send_packet.write(len(packet_serd).to_bytes(4, 'big', signed=False))
            self.curr_send_packet.write(packet_serd)
            self.curr_send_packet.seek(0, 0)

        for _ in range(128): # avoid sending more than 512kb in one go
            block = self.curr_send_packet.read(BLOCK_SIZE)
            if not block:
                self.curr_send_packet = None
                return

            amt_sent = self.connection.send(block)
            if amt_sent < len(block):
                self.curr_send_packet.seek(amt_sent - len(block), 1)
                return

    def _try_from_recq(self, amt: int) -> typing.Optional[bytes]:
        """Tries to read the specified number of bytes from the receive queue.
        If this fails to get that many bytes the receive queue is effectively
        unaltered, otherwise the bytes are removed from the receive queue
        and returned"""

        if not self.curr_rec:
            return None
        if len(self.curr_rec) == 1 or len(self.curr_rec[0]) >= amt:
            # happy / most common case
            if len(self.curr_rec[0]) < amt:
                return None
            block = self.curr_rec.popleft()
            if len(block) == amt:
                return block

            self.curr_rec.appendleft(block[amt:])
            return block[:amt]

        result = io.BytesIO()
        curlen = 0
        while self.curr_rec:
            block = self.curr_rec.popleft()
            if curlen + len(block) == amt:
                # another happy / common case
                result.write(block)
                return result.getvalue()

            if curlen + len(block) < amt:
                result.write(block)
                continue

            result.write(block[:amt])
            self.curr_rec.appendleft(block[amt:])
            return result.getvalue()

        # didn't get enough data, but now the curr_rec queue is all merged
        # so we will get the top happy case
        self.curr_rec.appendleft(result.getvalue())
        return None

    def _handle_rec(self):
        for _ in range(128): # avoid reading more than 512kb in one go
            block = self.connection.recv(BLOCK_SIZE)
            if not block:
                self.connection.close()
                self.connection = None
                break
            self.curr_rec.append(block)
            if len(block) < BLOCK_SIZE:
                break

        for _ in range(8): # avoid parsing too many packets at once
            lenblock = self._try_from_recq(4)
            if not lenblock:
                return
            explen = int.from_bytes(lenblock, 'big', signed=False)
            block = self._try_from_recq(explen)
            if not block:
                self.curr_rec.appendleft(lenblock)
                return

            packet = ser.deserialize(block)
            if not isinstance(packet, packets.Packet):
                raise ValueError(f'got non-packet {packet} (type={type(packet)})')
            self.rec_queue.put(packet)

    def send(self, packet: packets.Packet):
        """Sends this client the specified packet"""
        if self.disconnected():
            return
        self.send_queue.put_nowait(ser.serialize(packet))

    def send_serd(self, packet_serd: bytes):
        """Sends this client the serialized packet"""
        if self.disconnected():
            return
        self.send_queue.put_nowait(packet_serd)

    def read(self) -> typing.Optional[packets.Packet]:
        """Returns the packet from the client if there is one"""
        return self.rec_queue.get_nowait() if not self.rec_queue.empty() else None

    def has_pending(self, read=True, write=True) -> bool:
        """Returns True if there are pending sends / receives, False otherwise"""
        if write and not self.send_queue.empty():
            # have things to send still
            return True
        if read and not self.rec_queue.empty():
            # have things that we've parsed but haven't been read() yet
            return True
        if write and self.curr_send_packet is not None:
            # in the middle of sending something
            return True
        if read and self.curr_rec:
            # have things not yet parsed / incomplete
            return True
        return False