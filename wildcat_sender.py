import common
import threading
import struct
import zlib

class wildcat_sender(threading.Thread):
    def __init__(self, allowed_loss, window_size, my_tunnel, my_logger):
        super(wildcat_sender, self).__init__()
        self.allowed_loss = allowed_loss
        self.window_size = window_size
        self.my_tunnel = my_tunnel
        self.my_logger = my_logger
        self.die = False
        # add as needed
        # seq num counter, start at 0
        self.next_seq = 0
    
    def new_packet(self, packet_byte_array):
        ''' invoked when user sends a payload
        (Send with self.my_tunnel.magic_send(packet)) '''
        # build MSG: 2B seq (uint16), payload, 2B checksum (CRC32 & OxFFFF)
        # take curr seq
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
        self.my_tunnel.magic_send(packet_byte_array)
        # adv seq num (wrap at 2^16)
        self.next_seq = (self.next_seq + 1) & 0xFFFF

    def receive(self, packet_byte_array):
        ''' invoked when an ACK arrives '''
        # TODO: your implementation comes here
        print(f"received : {packet_byte_array}")
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