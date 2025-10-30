import threading
import struct
import zlib


class wildcat_sender(threading.Thread):
    def __init__(self, allowed_loss, window_size, my_tunnel, my_logger):
        super(wildcat_sender, self).__init__()
        self.allowed_loss = allowed_loss

        self.window_size = window_size
        self.inflight_window = {}
        self.snd_wnd_seq_num = 0

        self.my_tunnel = my_tunnel
        self.my_logger = my_logger
        self.die = False
        # add as needed
        # start of cwnd (lowest#/oldest unACK'd pkt)
        self.base = 0

    def new_packet(self, packet_byte_array):
        ''' invoked when user sends a payload
        (Send with self.my_tunnel.magic_send(packet)) '''
        # build MSG: 2B seq (uint16), payload, 2B checksum (CRC32 & OxFFFF)
        # take curr seq (lowest 16 bits)
        seq = self.snd_wnd_seq_num & 0xFFFF
        # pack seq num as 2Bs (big-endian)
        seq_bytes = struct.pack("!H", seq)
        # ensure payload is bytes
        payload_bytes = bytes(packet_byte_array)
        # body used for checksum = seq + payload
        body = seq_bytes + payload_bytes

        checksum = compute_checksum(body)
        ck_bytes = struct.pack("!H", checksum)

        # final MSG = seq(2) + payload + checksum(2)
        msg = body + ck_bytes
        # adv seq num (wrap at 2^16)
        self.snd_wnd_seq_num = (self.snd_wnd_seq_num + 1) & 0xFFFF

        self.send_packet(msg)

    def send_packet(self, byte_array_with_headers):
        print(f"sending : {byte_array_with_headers}")
        seq_num = get_seq_num(byte_array_with_headers)

        # actual send
        self.my_tunnel.magic_send(byte_array_with_headers)

        timeout = threading.Timer(0.5, self.timeout_callback, args=(byte_array_with_headers,))
        timeout.start()
        self.inflight_window[seq_num] = (byte_array_with_headers, timeout)

    def timeout_callback(self, byte_array_with_headers):
        print(f"timed out for : {get_seq_num(byte_array_with_headers)}, resending...")
        self.send_packet(byte_array_with_headers)
    
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
        print(f"sender received : {packet_byte_array}")

        if not does_checksum_match(packet_byte_array):
            print("Dropping corrupted ack")
            return

        seq_num = get_seq_num(packet_byte_array)

        # rec'd ACK so adv base (bottom of send window)
        self.adv_base(self)
        self.confirm_packet_delivery(seq_num)

        #TODO: remove any skipped packets from inflight_window, based on ack data seq_num or bytearray

    def confirm_packet_delivery(self, seq_num):
        if seq_num in self.inflight_window:
            timeout = self.inflight_window[seq_num][1]
            timeout.cancel()
            del self.inflight_window[seq_num]
        else:
            print("Ack for untracked seq_num, ignoring")

    def run(self):
        ''' background loop for timers/retransmissions
        Retransmit unacked packets within 0.5 s '''
        while not self.die:
            # TODO: your implementation comes here
            pass
    
    def join(self):
        self.die = True
        super().join()

def compute_checksum(byte_array) -> int:
    # keep lower 16 bits to fit in 2 byte checksum header
    return zlib.crc32(byte_array) & 0xFFFF

def does_checksum_match(byte_array) -> bool:
    return get_ck_sum(byte_array) == compute_checksum(get_seq_num_and_payload(byte_array))

def get_seq_num(byte_array) -> int:
    return struct.unpack("!H", byte_array[:2])[0]

def get_ck_sum(byte_array) -> int:
    return struct.unpack("!H", byte_array[-2:])[0]

def get_payload(byte_array) -> bytes:
    return byte_array[2:-2]

def get_seq_num_and_payload(byte_array) -> bytes:
    return byte_array[0:-2]