import RPi.GPIO as GPIO
import time

def generate_square_wave(gpio_pins, base_frequency):
    try:
        # Setup GPIO
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(gpio_pins, GPIO.OUT)

        # Calculate half-periods for each pin (in seconds)
        half_periods = [1.0 / (2 * (base_frequency / (2 ** i))) for i in range(len(gpio_pins))]

        print("Generating square waves. Press Ctrl+C to stop.")
        # Track the last toggle time for each pin
        last_toggle_time = [time.time()] * len(gpio_pins)
        pin_states = [False] * len(gpio_pins)  # Track the current state (high or low) of each pin

        while True:
            current_time = time.time()
            # Check each pin and toggle if enough time has passed
            for i, (pin, half_period) in enumerate(zip(gpio_pins, half_periods)):
                if current_time - last_toggle_time[i] >= half_period:
                    # Toggle the pin state
                    pin_states[i] = not pin_states[i]
                    GPIO.output(pin, pin_states[i])
                    # Update the last toggle time
                    last_toggle_time[i] = current_time
    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected. Stopping square wave generation.")
    finally:
        # Cleanup GPIO
        GPIO.cleanup()
        print("GPIO cleaned up and program exited.")

if __name__ == "__main__":
    try:
        # Get user inputs
        gpio_pins_input = input("Enter four GPIO pin numbers (BOARD numbering), separated by spaces: ")
        gpio_pins = [int(pin) for pin in gpio_pins_input.strip().split()]

        if len(gpio_pins) != 4:
            print("Please enter exactly four GPIO pin numbers.")
            exit(1)

        base_frequency = float(input("Enter base frequency in Hz: "))

        generate_square_wave(gpio_pins, base_frequency)
    except ValueError:
        print("Invalid input. Please enter numeric values.")