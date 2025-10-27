import math

import common
import threading
import struct
import zlib

from wildcat_sender import get_seq_num, get_ck_sum, does_checksum_match, get_payload


class wildcat_receiver(threading.Thread):
    def __init__(self, allowed_loss, window_size, my_tunnel, my_logger):
        super(wildcat_receiver, self).__init__()
        self.allowed_loss = allowed_loss
        self.window_size = window_size
        # assume sequence starts at 0
        self.rcv_wnd_seq_num = 0
        self.received_window = {}

        self.my_tunnel = my_tunnel
        self.my_logger = my_logger
        self.die = False
        # add as needed

    def receive(self, packet_byte_array):
        print(f"received : {packet_byte_array}")

        if not does_checksum_match(packet_byte_array):
            return # drop corrupted packets

        seq_num = get_seq_num(packet_byte_array)
        if self.is_outside_window(seq_num):
            return # drop packet if outside window

        payload = get_payload(packet_byte_array)
        self.received_window[seq_num] = payload
        self.process_window()

        ack = self.create_ack_packet(seq_num)
        self.my_tunnel.magic_send(ack)

    def is_outside_window(self, seq_num):
        distance = (seq_num - self.rcv_wnd_seq_num) & 0xFFFF # handles wrap around
        return distance > self.window_size

    def process_window(self):
        # TODO: this assumes every packet must arrive, but this protocol supports % loss
        while self.received_window[self.rcv_wnd_seq_num] is not None:
            self.my_logger.commit(self.received_window[self.rcv_wnd_seq_num])
            del self.received_window[self.rcv_wnd_seq_num]
            self.rcv_wnd_seq_num = (self.rcv_wnd_seq_num + 1) & 0xFFFF

    def create_ack_packet(self, ack_seq_num):
        seq_bytes = struct.pack("!H", ack_seq_num)
        bitmap = self.create_ack_bitmaps()
        body = seq_bytes + bitmap

        checksum = zlib.crc32(body) & 0xFFFF
        ck_bytes = struct.pack("!H", checksum)
        return body + ck_bytes


    def create_ack_bitmaps(self):
        bitmap = 0
        for seq_num in self.received_window.keys():
            bitmap |= (1 << (seq_num - self.rcv_wnd_seq_num)) # TODO: probably an issue here with wraparound

        # Calculate number of bytes needed for window_size bits
        num_bytes = math.ceil(self.window_size / 8) # Round up to nearest byte
        return bitmap.to_bytes(num_bytes, byteorder='big')


    def run(self):
        ''' background loop as needed 
        Send with self.my_tunnel.magic_send(packet) 
        When a payload is delivered in order, call self.my_logger.commit(payload) (grading counts only committed data)'''
        while not self.die:
            # TODO: your implementation comes here
            pass
            
    def join(self):
        self.die = True
        super().join()
