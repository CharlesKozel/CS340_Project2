import common
import threading
import struct

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
        seq_num = self.get_seq_num(packet_byte_array)
        self.my_tunnel.magic_send(packet_byte_array)

    def get_seq_num(self, byte_array):
        return struct.unpack("!H", byte_array[:2])[0]

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