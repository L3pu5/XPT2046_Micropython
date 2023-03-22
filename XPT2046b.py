#
#  XPT2046b. 
#      By L3pu5, L3pu5_Hare
#
# A simple Python wrapper for the XPT2046 touch driver bound to the SPI interface IM[2:0] 101 for chipsets such as
# those ubuqituous ones on Aliexpress.

from bnuuyDrivers_micropython.RECTANGLE import RECTANGLE

class Active_Zone():
    rect        = 0
    callback    = 0

    def __init__(self, rect, cb):
        self.rect = rect
        self.callback = cb

    def check_and_do_work(self, point_tuple):
        if(self.rect.contains_point(point_tuple[0], point_tuple[1])):
            try:
                self.callback()
            except:
                print("An exception occured in touch callback.")


class Touch():
    # Command constants from XPT2046 datasheet (Limited)
    # Commands are 1 8 bit byte.
    # [S|A2|A1|A0|MODE|SER/DFR|PD1|PD0]
    # S bit         -> Start bit, high
    # A2, A1, A0    -> Channel select bits
    # MODE          -> 12/8 bit conversion. 12 LOW, 8 HIGH
    # SER/DFR       -> Controls multiplexer input.See   Table1/2
    # PD1, PD0      -> Power down Mode select bits.     Table 5
    READ_Y          = 0b10010000
    READ_X          = 0b11010000
    #8 BITS
    READ_Y_8        = 0b10011000
    READ_X_8        = 0b11011000

    INVERT_Y        = False
    INVERT_X        = False

    BUFFER          = bytearray(3)
    BYTE            = bytearray(1)
    
    screen_width_px                   = 320
    screen_height_px                  = 480
    max_board_output_width            = 0
    max_board_output_height           = 0
    clipping                          = 50 #board units

    # Active Zones are bnuuyDriver RECTANGLE objects which contain a bounds.
    # These are iterated on each frame for touch.
    Active_Zones                      = []

    PRECOMPUTED_BOARD_SPECS = {
        # Format
        # (max_board_output_width, max_board_output_height)
        "default": (1850,1900),
        "3.5 inch TFT LCD Module": (1850,1900)
    }

    PRECOMPUTED_GRAPHIC_DRIVER_SPECS = {
        #Format 
        # (INVERT_X, INVERT_Y)
        "default": (False, False),
        "ILI9488b": (False, True)
    }

    def __init__(self, spi, cs, irq=None, width=320, height=480, board="default", driver="ILI9488b"):
        # IO
        self.spi = spi
        self.cs = cs
        self.irq = irq
        self.screen_width_px = width
        self.screen_height_px = height
        self.cs.init(self.cs.OUT, value=1)
        self.irq.init(self.irq.IN, value=1)
        # Board Specs (Width,Height)
        self.max_board_output_height = self.PRECOMPUTED_BOARD_SPECS[board][0]
        self.max_board_output_width = self.PRECOMPUTED_BOARD_SPECS[board][1]
        # Driver Specs (Invert_X, Invert_Y)
        self.INVERT_X = self.PRECOMPUTED_GRAPHIC_DRIVER_SPECS[driver][0]
        self.INVERT_Y = self.PRECOMPUTED_GRAPHIC_DRIVER_SPECS[driver][1]
        #Clipping
        self.clipping = 50

    # Pixel Mapping

    def get_point_board_8(self):
        x = int.from_bytes(self.write_command_8(self.READ_X_8), "big")
        y = int.from_bytes(self.write_command_8(self.READ_Y_8), "big")
        return (x,y)

    def get_point_screen(self):
        point = self.get_point_board()
        x = (point[0] / self.max_board_output_width * self.screen_width_px)
        y = (point[1] / self.max_board_output_height * self.screen_height_px)
        if self.INVERT_X:
            x = self.screen_width_px - x;
        if self.INVERT_Y:
            y = self.screen_height_px - y;
        return (x,y)

    def get_point_board(self):
        x = self.write_command_12(self.READ_X)
        if x > (self.max_board_output_width - self.clipping):
            x = self.max_board_output_width
        y = self.write_command_12(self.READ_Y)
        if y > (self.max_board_output_height - self.clipping):
            y = self.max_board_output_height
        if (x - self.clipping) < 0:
            x = 0
        if (y - self.clipping) < 0:
            y = 0
        return (x,y)

    def get_point_board_X(self):
        x = self.write_command_X(self.READ_X)
        y = self.write_command_X(self.READ_Y)
        return (x,y)

    # Responsive domains
    # Returns the index of the activezone
    def register_active_zone(self, active_zone):
        self.Active_Zones.append(active_zone)

    def deregister_active_zone(self, active_zone):
        self.Active_Zones.remove(active_zone)

    # Hearbeat, call each frame you want TouchIO.
    def heartbeat(self):
        position = self.get_point_screen()
        for i in self.Active_Zones:
            i.check_and_do_work(position)
        return position

    # Commands

    def write_command(self, command) -> bytes:
        command_buffer = bytearray(3)
        command_buffer[0] = command
        self.cs.value(0)
        self.spi.write_readinto(command_buffer, self.BUFFER)
        self.cs.value(1)
        return self.BUFFER
    
    def write_command_12(self, command) -> int:
        command_buffer = bytearray(3)
        command_buffer[0] = command
        self.cs.value(0)
        self.spi.write_readinto(command_buffer, self.BUFFER)
        self.cs.value(1)
        return (self.BUFFER[1] << 4) | (self.BUFFER[2] >> 4)      
    
    def write_command_X(self, command) -> int:
        command_buffer = bytearray(3)
        command_buffer[0] = command
        self.cs.value(0)
        self.spi.write_readinto(command_buffer, self.BUFFER)
        self.cs.value(1)
        return (self.BUFFER[1] * 256 + self.BUFFER[2]) >> (15 - 12) 

    def write_command_8(self, command) -> bytes:
        command_buffer = bytearray(1)
        command_buffer[0] = command
        self.cs.value(0)
        self.spi.write_readinto(command_buffer, self.BYTE)
        self.cs.value(1)
        return self.BYTE