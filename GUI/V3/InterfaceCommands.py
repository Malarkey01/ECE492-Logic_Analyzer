# InterfaceCommands.py

def get_trigger_edge_command(trigger_modes):
    """
    Existing function to determine the edge of buttons selected and return the corresponding command integer.

    The LSB represents the edge of channel 1 while the MSB represents channel 8.
    If the button is on 'Rising Edge', the bit value will be 1.
    If it's on 'Falling Edge' or 'No Trigger', the bit will be 0.
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

    Parameters:
    - trigger_modes: List of 8 strings, each can be 'Rising Edge', 'Falling Edge', or 'No Trigger'

    Returns:
    - An integer between 0 and 255 representing the trigger pins
    """
    command_value = 0
    for idx in range(8):
        mode = trigger_modes[idx]
        if mode in ('Rising Edge', 'Falling Edge'):
            command_value |= 1 << idx  # Set bit idx if trigger is enabled
    return command_value
