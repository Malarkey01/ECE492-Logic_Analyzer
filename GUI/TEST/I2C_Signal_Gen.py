import RPi.GPIO as GPIO
import time

# I2C pin configuration (BOARD numbering)
SDA_PIN = 3  # Physical pin 3
SCL_PIN = 5  # Physical pin 5

# Bit-banging delay (in seconds)
# BIT_DELAY = 0.0001  # 100 microseconds, adjust as needed for signal speed
BIT_DELAY = 0.004

def i2c_start():
    """Simulate an I2C start condition."""
    GPIO.output(SDA_PIN, GPIO.HIGH)
    GPIO.output(SCL_PIN, GPIO.HIGH)
    time.sleep(BIT_DELAY)
    GPIO.output(SDA_PIN, GPIO.LOW)
    time.sleep(BIT_DELAY)
    GPIO.output(SCL_PIN, GPIO.LOW)
    time.sleep(BIT_DELAY)

def i2c_stop():
    """Simulate an I2C stop condition."""
    GPIO.output(SDA_PIN, GPIO.LOW)
    GPIO.output(SCL_PIN, GPIO.HIGH)
    time.sleep(BIT_DELAY)
    GPIO.output(SDA_PIN, GPIO.HIGH)
    time.sleep(BIT_DELAY)

def i2c_write_byte(byte):
    """Simulate writing a byte over I2C."""
    for bit in range(8):
        # Write each bit, MSB first
        bit_value = (byte & (1 << (7 - bit))) != 0
        GPIO.output(SDA_PIN, bit_value)
        time.sleep(BIT_DELAY)
        # Toggle the clock
        GPIO.output(SCL_PIN, GPIO.HIGH)
        time.sleep(BIT_DELAY)
        GPIO.output(SCL_PIN, GPIO.LOW)
        time.sleep(BIT_DELAY)
    
    # Simulate ACK bit (from "device")
    GPIO.output(SDA_PIN, GPIO.HIGH)  # Release SDA for ACK
    time.sleep(BIT_DELAY)
    GPIO.output(SCL_PIN, GPIO.HIGH)  # Clock pulse for ACK
    time.sleep(BIT_DELAY)
    GPIO.output(SCL_PIN, GPIO.LOW)
    time.sleep(BIT_DELAY)
    GPIO.output(SDA_PIN, GPIO.LOW)  # Prepare SDA for next byte

def generate_i2c_signal(hex_code):
    """Generate a simulated I2C signal sequence."""
    # Set up GPIO
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(SDA_PIN, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(SCL_PIN, GPIO.OUT, initial=GPIO.HIGH)

    try:
        print("Generating I2C signals. Press Ctrl+C to stop.")
        while True:
            # Simulate I2C communication: Start -> Write Byte -> Stop
            i2c_start()
            i2c_write_byte(hex_code)  # Use the user-provided byte
            i2c_stop()

            time.sleep(0.25)  # Delay between transmissions
    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected. Stopping I2C signal generation.")
    finally:
        # Cleanup GPIO
        GPIO.cleanup()
        print("GPIO cleaned up and program exited.")

if __name__ == "__main__":
    try:
        # Prompt the user for the hex code
        hex_input = input("Enter the hex code to send (e.g., '0xA5' or 'A5'): ")
        hex_code = int(hex_input, 16)
        generate_i2c_signal(hex_code)
    except ValueError:
        print("Invalid hex code entered. Please enter a valid hexadecimal value.")
