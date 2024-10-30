import RPi.GPIO as GPIO
import time

# SPI pin configuration (BOARD numbering)
MOSI_PIN = 19  # Physical pin 19
SCLK_PIN = 23  # Physical pin 23
CS_PIN = 24    # Physical pin 24 (optional, can be used as Chip Select)

# Bit-banging delay (in seconds)
BIT_DELAY = 0.0001  # Adjust as needed for desired SPI clock speed

def spi_transfer(byte_data):
    """Simulate SPI transfer by sending one byte."""
    # Pull CS low to select the slave device
    GPIO.output(CS_PIN, GPIO.LOW)
    time.sleep(BIT_DELAY)

    for bit in range(8):
        # Set clock low before changing data
        GPIO.output(SCLK_PIN, GPIO.LOW)
        time.sleep(BIT_DELAY)

        # Write each bit, MSB first
        bit_value = (byte_data & (1 << (7 - bit))) != 0
        GPIO.output(MOSI_PIN, bit_value)
        time.sleep(BIT_DELAY)

        # Clock high: Data is read by slave on rising edge
        GPIO.output(SCLK_PIN, GPIO.HIGH)
        time.sleep(BIT_DELAY)

    # Set clock low after transfer
    GPIO.output(SCLK_PIN, GPIO.LOW)
    time.sleep(BIT_DELAY)

    # Pull CS high to deselect the slave device
    GPIO.output(CS_PIN, GPIO.HIGH)
    time.sleep(BIT_DELAY)

def generate_spi_signal(hex_code):
    """Generate SPI signals by sending the provided hex code."""
    # Set up GPIO
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(MOSI_PIN, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(SCLK_PIN, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(CS_PIN, GPIO.OUT, initial=GPIO.HIGH)  # CS is active low

    try:
        print("Generating SPI signals. Press Ctrl+C to stop.")
        while True:
            spi_transfer(hex_code)
            time.sleep(0.5)  # Delay between transfers
    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected. Stopping SPI signal generation.")
    finally:
        # Cleanup GPIO
        GPIO.cleanup()
        print("GPIO cleaned up and program exited.")

if __name__ == "__main__":
    try:
        # Prompt the user for the hex code
        hex_input = input("Enter the hex code to send (e.g., '0xA5' or 'A5'): ")
        hex_code = int(hex_input, 16)
        generate_spi_signal(hex_code)
    except ValueError:
        print("Invalid hex code entered. Please enter a valid hexadecimal value.")
