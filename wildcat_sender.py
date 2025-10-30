import threading
import struct
import zlib


class wildcat_sender(threading.Thread):
    def __init__(self, allowed_loss, window_size, my_tunnel, my_logger):
        super(wildcat_sender, self).__init__()
        self.allowed_loss = allowed_loss
        self.my_tunnel = my_tunnel
        self.my_logger = my_logger
        self.die = False
        self.window_size = window_size

        self.inflight_window = {}
        self.snd_wnd_seq_num = 0 # tracks seq num for sent packets
        self.rcv_wnd_seq_num = 0 # tracks acks indicating what receiver window is at
        self.packet_queue = []


    def new_packet(self, packet_byte_array):
        ''' invoked when user sends a payload
        (Send with self.my_tunnel.magic_send(packet)) '''

        if self.is_rcv_wnd_full():
            print("SND: Rcv window full, queueing packet")
            self.queue_pkt(packet_byte_array)
            return

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
        self.print_window()

    def print_window(self):
        print(f"SND: window : {[seq_num for seq_num in self.inflight_window.keys()]}")

    def send_packet(self, byte_array_with_headers):
        print(f"SND: sending : {get_seq_num(byte_array_with_headers)}")
        seq_num = get_seq_num(byte_array_with_headers)
        # actual send
        self.my_tunnel.magic_send(byte_array_with_headers)

        timeout = threading.Timer(0.5, self.timeout_callback, args=(byte_array_with_headers,))
        timeout.start()
        self.inflight_window[seq_num] = (byte_array_with_headers, timeout)

    def timeout_callback(self, byte_array_with_headers):
        print(f"SND: timed out for : {get_seq_num(byte_array_with_headers)}, resending...")
        self.send_packet(byte_array_with_headers)

    def receive(self, packet_byte_array):
        ''' invoked when an ACK arrives '''
        #print(f"sender received : {packet_byte_array}")

        if not does_checksum_match(packet_byte_array):
            print("SND: Dropping corrupted ack")
            return

        latest_rcv_seq_num = get_seq_num(packet_byte_array)
        print(f"SND: got ack for : {latest_rcv_seq_num}")

        if self.did_receiver_advance_seq_num(latest_rcv_seq_num):
            print("SND: receiver advanced seq num")
            # sender advanced its window, drop any inflight packet tracking outside the receiver window
            while self.rcv_wnd_seq_num != latest_rcv_seq_num:
                print(f"SND: dropping packet {self.rcv_wnd_seq_num} from window")
                timeout = self.inflight_window[self.rcv_wnd_seq_num][1]
                timeout.cancel()
                del self.inflight_window[self.rcv_wnd_seq_num]
                self.rcv_wnd_seq_num = (self.rcv_wnd_seq_num + 1) & 0xFFFF

        # Handle other packets whose ACKs might have been lost, but we know they were received b/c of the window_bitmap
        rcv_window_bitmap = extract_window_bitmap(packet_byte_array)
        for window_index in range(self.window_size):
            if rcv_window_bitmap & (1 << window_index):
                packet_seq_num = (latest_rcv_seq_num + window_index) & 0xFFFF
                if packet_seq_num in self.inflight_window:
                    timeout = self.inflight_window[packet_seq_num][1]
                    timeout.cancel()
                    del self.inflight_window[packet_seq_num]

        self.print_window()

        # Got an ACK, process queue to see if any more packets can be sent
        self.process_queue()

    def did_receiver_advance_seq_num(self, latest_rcv_seq_num):
        distance = (latest_rcv_seq_num - self.rcv_wnd_seq_num) & 0xFFFF
        return 0 < distance < 32768

    def is_rcv_wnd_full(self) -> bool:
        max_rcv_seq_num = (self.rcv_wnd_seq_num + self.window_size) & 0xFFFF
        snd_wnd_distance = (max_rcv_seq_num - self.snd_wnd_seq_num) & 0xFFFF
        # snd_wnd_distance > 0 => not full
        # <32768 b/c negative distance gets converted to 65536 - distance, assume >32768(2^15) is negative => full
        return not (0 < snd_wnd_distance < 32768)

    def queue_pkt(self, packet):
        # if next_seq > upper limit of rcv wnd (est_rcv_wnd_range), wait to send until window moves forward
        self.packet_queue.append(packet)

    def process_queue(self):
        while len(self.packet_queue) > 0 and not self.is_rcv_wnd_full():
            packet = self.packet_queue.pop(0)
            self.new_packet(packet) #TODO: consider new_packet to only be called externally, refactor logic accordingly

    def run(self):
        ''' background loop for timers/retransmissions
        Retransmit unacked packets within 0.5 s '''
        while not self.die:
            pass
    
    def join(self):
        self.die = True
        super().join()

def extract_window_bitmap(byte_array) -> int:
    return int.from_bytes(get_payload(byte_array), byteorder='big')

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