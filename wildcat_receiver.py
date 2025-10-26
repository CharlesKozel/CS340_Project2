import common
import threading

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
        print(f"received : {packet_byte_array}")
        self.my_tunnel.magic_send(packet_byte_array)

    def run(self):
        while not self.die:
            # TODO: your implementation comes here
            pass
            
    def join(self):
        self.die = True
        super().join()