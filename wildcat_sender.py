import common
import threading
import struct
import zlib
import random

MAX_UINT16 = 65535

class wildcat_sender(threading.Thread):
    def __init__(self, allowed_loss, window_size, my_tunnel, my_logger):
        super(wildcat_sender, self).__init__()
        self.allowed_loss = allowed_loss

        self.window_size = window_size
        self.inflight_window = {}

        self.my_tunnel = my_tunnel
        self.my_logger = my_logger
        self.die = False
        # add as needed
        # start of cwnd (lowest#/oldest unACK'd pkt)
        self.base = 0
        # seq num counter, start at 0 (end of cwnd, next seq num to send)
        self.next_seq = 0

    def new_packet(self, packet_byte_array):
        ''' invoked when user sends a payload
        (Send with self.my_tunnel.magic_send(packet)) '''
        # build MSG: 2B seq (uint16), payload, 2B checksum (CRC32 & OxFFFF)
        # take curr seq (lowest 16 bits)
        seq = self.next_seq & 0xFFFF
        # pack seq num as 2Bs (big-endian)
        seq_bytes = struct.pack("!H", seq)
        # ensure payload is bytes
        payload_bytes = bytes(packet_byte_array)
        # body used for checksum = seq + payload
        body = seq_bytes + payload_bytes
        # compute checksum & keep lower 16 bits
        checksum = zlib.crc32(body) & 0xFFFF
        ck_bytes = struct.pack("!H", checksum)
        # final MSG = seq(2) + payload + checksum(2)
        msg = body + ck_bytes

        print(f"sending : {packet_byte_array}")
        # send thru magic tunnel
        seq_num = self.get_and_inc_seq_num()
        self.my_tunnel.magic_send(packet_byte_array)
        # adv seq num (wrap at 2^16)
        self.next_seq = (self.next_seq + 1) & 0xFFFF

        timeout = threading.Timer(0.5, self.timeout_callback, args=(packet_byte_array,))
        timeout.start()

        self.inflight_window[seq_num] = (packet_byte_array, timeout)

    def send_packet(self, byte_array_with_headers):
        seq_num = self.get_seq_num(byte_array_with_headers)
        self.my_tunnel.magic_send(byte_array_with_headers)

        timeout = threading.Timer(0.5, self.timeout_callback, args=(byte_array_with_headers,))
        timeout.start()
        self.inflight_window[seq_num] = (byte_array_with_headers, timeout)


    def get_seq_num(self, byte_array):
        return struct.unpack("!H", byte_array[:2])[0]


    def timeout_callback(self, byte_array):
        print(f"timed out for : {byte_array}")
        pass
    
    def adv_base(self):
        '''Advance base to lowest unACK'd seq num. If none, then base is next_seq'''
        # everything ACKd, base catches up to next_seq
        if not self.inflight_window:
            self.base = self.next_seq & 0xFFFF
            return
        
        # move base up 1 until it's in the window (meaning has reached the lowest unACKd) or it reaches end of window (so catches up w/ next one to send which is the 1st outside the window since all in window were ACKd & those outside aren't sent yet so must be unACKd)
        while (self.base not in self.inflight_window) and (self.base != self.next_seq):
            self.base = (self.base + 1) & 0xFFFF

    def receive(self, packet_byte_array):
        ''' invoked when an ACK arrives '''
        # TODO: your implementation comes here
        print(f"received : {packet_byte_array}")
        # move window up b/c received ACK
        self.adv_base(self)
        pass
    
    def run(self):
        ''' background loop for timers/retransmissions
        Retransmit unacked packets within 0.5 s '''
        while not self.die:
            # TODO: your implementation comes here
            pass
    
    def join(self):
        self.die = True
        super().join()