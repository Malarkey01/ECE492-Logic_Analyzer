#include <msp430.h> 
#include <stdint.h>

const uint16_t ACLKFreq = 32768;
const uint32_t SMCLKFreq = 1000000;
void msp_init()
{
    WDTCTL = WDTPW | WDTHOLD;            // Stop watchdog timer

    P1DIR |= BIT6;                       // set to output
    P1REN &= ~BIT6;
    P1OUT &= ~BIT6;

    //Timer for delaying
    //      stopMode|1 divider|ACLK|clear
    TA0CTL = MC_0 | ID_0 | TASSEL_1 | TACLR;
    P1SEL1 |= BIT6;                      //connect pin 1.6 to timer A0
    P1SEL0 |= BIT6;
    //enable interrupt for channel 0
    TA0CCTL1 |= OUTMOD_3 | CCIE;
    PM5CTL0 &= ~LOCKLPM5;                // Unlock ports from power manager
    __enable_interrupt();
}
/*
 * sets frequency of the ta0ccr value
 */
void setFrequency(float freq){
                                         //check if frequency is higher than 32 kHz, set up SMCLK for that
    uint16_t ticks;
    if (freq > 7){
        TA0CTL &= ~TASSEL_1;             //clears previous clock setting
        TA0CTL |= TASSEL_2 | TACLR;      //switches to SMCLK
        ticks = SMCLKFreq/freq;          // formula used to grab the amount of ticks needed to cover the given frequency
    }
    else {
        TA0CTL &= ~TASSEL_2;             //clears previous clock setting
        TA0CTL |= TASSEL_1 | TACLR;      //switches to ACLK
        ticks = ACLKFreq/freq;           // formula used to grab the amount of ticks needed to cover the given frequency
    }
    int ticks2 = ticks/2;                // divide ticks by two to account for turning LED on and off within the same frequency
    TA0CCR1 = ticks2;
    TA0CCR0 = ticks;                     // timer will raise flag once tick value has been reached
}
int main(void)
{
	msp_init();
	//1 Hz - 500 kHz
	setFrequency(75000);
    //start timer in up mode
    TA0CTL |= MC_1;
	while(1){
	    __low_power_mode_1();
	}
}
