# InterfaceCommands.py

def get_trigger_edge_command(trigger_modes):
    """
    Determines the edge of buttons selected and returns the corresponding command integer.

    The LSB represents the edge of channel 1 while the MSB represents channel 8.
    If the button is on 'Rising Edge', the bit value will be 1.
    If it's on 'Falling Edge' or 'No Trigger', the bit will be 0.
    This 8-bit value is converted to an int and can be sent as a character.
    """
    command_value = 0
    for idx in range(8):
        mode = trigger_modes[idx]
        if mode == 'Rising Edge':
            command_value |= 1 << idx  # Set bit idx if Rising Edge
    return command_value

def get_trigger_pins_command(trigger_modes):
    """
    Determines which channels have triggers enabled and returns the corresponding command integer.

    The LSB represents channel 1, and the MSB represents channel 8.
    If the button is either 'Rising Edge' or 'Falling Edge', the bit value is 1.
    If it's 'No Trigger', the bit will be 0.
    This 8-bit value is converted to an int and can be sent as a character.
    """
    command_value = 0
    for idx in range(8):
        mode = trigger_modes[idx]
        if mode in ('Rising Edge', 'Falling Edge'):
            command_value |= 1 << idx  # Set bit idx if trigger is enabled
    return command_value

def get_num_samples_command(num_samples):
    """
    Splits the number of samples (1-1023) into two parts:
    - First part: bits 9-8 (MSBs), representing values 0-3
    - Second part: bits 7-0 (LSBs), representing values 0-255
    Returns a tuple (msb_value, lsb_value) where:
    - msb_value is an integer between 0 and 3
    - lsb_value is an integer between 0 and 255
    """
    if not (1 <= num_samples <= 1023):
        raise ValueError("Number of samples must be between 1 and 1023")

    msb_value = (num_samples >> 8) & 0b11  # Extract bits 9-8
    lsb_value = num_samples & 0xFF         # Extract bits 7-0
    return msb_value, lsb_value
