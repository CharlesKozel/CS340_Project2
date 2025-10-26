import common
import threading
import struct
import zlib

class wildcat_receiver(threading.Thread):
    def __init__(self, allowed_loss, window_size, my_tunnel, my_logger):
        super(wildcat_receiver, self).__init__()
        self.allowed_loss = allowed_loss
        self.window_size = window_size
        self.my_tunnel = my_tunnel
        self.my_logger = my_logger
        self.die = False
        # add as needed

    def receive(self, packet_byte_array):
        ''' invoked when a MSG arrives
        Drop packets outside the receiver window '''
        print(f"received : {packet_byte_array}")

        # extract seq num & ck sum
        seq_num = self.get_seq_num(packet_byte_array)
        ck_sum = self.get_ck_sum(packet_byte_array)

        # compute checksum over seq + payload (excl. trailing cksum)
        calc_ck = zlib.crc32(packet_byte_array[0:-2]) & 0xFFFF

        # drop corrupted pkts
        if calc_ck != ck_sum:
            return
        
        # extract payload (btw seq & ck)
        payload = packet_byte_array[2:-2]

        self.my_tunnel.magic_send(packet_byte_array)

    def get_seq_num(self, byte_array):
        return struct.unpack("!H", byte_array[:2])[0]
    
    def get_ck_sum(self, byte_array):
        return struct.unpack("!H", byte_array[-2:])[0]

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