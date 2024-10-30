import RPi.GPIO as GPIO
import time
import sys

# UART pin configuration (BOARD numbering)
TX_PIN = 8  # Physical pin 8 (GPIO14 TXD)

def uart_transmit(message, baud_rate, data_bits, stop_bits):
    # Calculate the bit duration
    bit_duration = 1.0 / baud_rate

    # Set up GPIO
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(TX_PIN, GPIO.OUT, initial=GPIO.HIGH)  # Idle state is HIGH

    try:
        print("Transmitting message. Press Ctrl+C to stop.")
        while True:
            for char in message:
                # Start bit
                GPIO.output(TX_PIN, GPIO.LOW)
                time.sleep(bit_duration)

                # Data bits
                ascii_val = ord(char)
                for i in range(data_bits):
                    bit_val = (ascii_val >> i) & 0x01
                    GPIO.output(TX_PIN, bit_val)
                    time.sleep(bit_duration)

                # Stop bits
                for _ in range(stop_bits):
                    GPIO.output(TX_PIN, GPIO.HIGH)
                    time.sleep(bit_duration)

            # Small delay between messages
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nTransmission stopped by user.")
    finally:
        # Cleanup GPIO
        GPIO.cleanup()
        print("GPIO cleaned up and program exited.")

def get_user_input():
    try:
        message = input("Enter the message to send: ")
        if not message:
            print("Message cannot be empty.")
            sys.exit(1)

        baud_rate_input = input("Enter the baud rate (e.g., 9600) [Default: 9600]: ")
        baud_rate = int(baud_rate_input) if baud_rate_input else 9600

        data_bits_input = input("Enter the number of data bits (5-8) [Default: 8]: ")
        data_bits = int(data_bits_input) if data_bits_input else 8
        if data_bits < 5 or data_bits > 8:
            print("Data bits must be between 5 and 8.")
            sys.exit(1)

        stop_bits_input = input("Enter the number of stop bits (0-3) [Default: 1]: ")
        stop_bits = int(stop_bits_input) if stop_bits_input else 1
        if stop_bits < 0 or stop_bits > 3:
            print("Stop bits must be between 0 and 3.")
            sys.exit(1)

        return message, baud_rate, data_bits, stop_bits
    except ValueError:
        print("Invalid input. Please enter numeric values where required.")
        sys.exit(1)

if __name__ == "__main__":
    message, baud_rate, data_bits, stop_bits = get_user_input()
    uart_transmit(message, baud_rate, data_bits, stop_bits)
