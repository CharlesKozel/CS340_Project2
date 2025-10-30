import math

import threading
import struct
import zlib

from wildcat_sender import get_seq_num, get_ck_sum, does_checksum_match, get_payload


class wildcat_receiver(threading.Thread):
    def __init__(self, allowed_loss, window_size, my_tunnel, my_logger):
        super(wildcat_receiver, self).__init__()
        self.allowed_loss = allowed_loss
        self.window_size = window_size

        self.rcv_wnd_seq_num = 0
        self.received_window = {}

        self.my_tunnel = my_tunnel
        self.my_logger = my_logger
        self.die = False

        self.count_success = 0
        self.count_fail = 0

    def receive(self, packet_byte_array):
        print(f"received : {packet_byte_array}")

        if not does_checksum_match(packet_byte_array):
            print("Dropping corrupted packet")
            return # drop corrupted packets

        seq_num = get_seq_num(packet_byte_array)
        if self.is_outside_window(seq_num):
            return # drop packet if outside window

        payload = get_payload(packet_byte_array)
        self.received_window[seq_num] = payload
        self.process_window()

        ack = self.create_ack_packet()
        self.my_tunnel.magic_send(ack)

    def is_outside_window(self, seq_num):
        distance = (seq_num - self.rcv_wnd_seq_num) & 0xFFFF # handles wrap around
        return distance > self.window_size

    def process_window(self):
        # Process consecutive packets first
        while self.rcv_wnd_seq_num in self.received_window:
            self.my_logger.commit(self.received_window[self.rcv_wnd_seq_num])
            self.count_success += 1
            del self.received_window[self.rcv_wnd_seq_num]
            self.rcv_wnd_seq_num = (self.rcv_wnd_seq_num + 1) & 0xFFFF

        # Check if we can skip packets within allowed loss budget
        for could_skip_i in range(1, self.get_could_skip_N_packets() + 1):
            next_valid_seq_num = (self.rcv_wnd_seq_num + could_skip_i) & 0xFFFF
            if next_valid_seq_num in self.received_window:
                # Count all skipped packets as failures
                self.count_fail += could_skip_i
                # Process the found packet
                self.my_logger.commit(self.received_window[next_valid_seq_num])
                self.count_success += 1
                del self.received_window[next_valid_seq_num]
                self.rcv_wnd_seq_num = (next_valid_seq_num + 1) & 0xFFFF
                # Recursively process any consecutive packets after this
                return self.process_window()


    # maybe better way to implement this logic, but the idea is if you can skip N packets
    # and the average is will allowable, return that many N used to check if N + 1 are
    # already received. Then it will skip ahead and drop those <= N packets.
    def get_could_skip_N_packets(self)->int:
        count = 0
        # if avg=(success/(total +1-HYPOTHETICAL_FAIL)) > allowed_loss_avg => could allow +1 packet skip
        while (self.count_success / (self.count_success + self.count_fail + count + 1)) > ((100 - self.allowed_loss) /100 ):
            count += 1
        return count


    def create_ack_packet(self):
        seq_bytes = struct.pack("!H", self.rcv_wnd_seq_num)
        bitmap = self.create_ack_bitmap()
        body = seq_bytes + bitmap

        checksum = zlib.crc32(body) & 0xFFFF
        ck_bytes = struct.pack("!H", checksum)
        return body + ck_bytes


    def create_ack_bitmap(self) -> bytes:
        bitmap = 0
        for window_index in range(self.window_size):
            seq_bit_i = (self.rcv_wnd_seq_num + window_index) & 0xFFFF
            if seq_bit_i in self.received_window:
                bitmap |= (1 << window_index)

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
