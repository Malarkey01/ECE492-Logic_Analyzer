/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2024 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "usb_device.h"
#include "usbd_cdc_if.h"
/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */
uint16_t buttonState = 0;
#define BUFFER_SIZE 1024
uint16_t buffer[BUFFER_SIZE];
int bufferPointer = 0;
uint8_t Buff[10];
int trigger = 0;
int Period_T;
int period = 65536;
char msg[10];
char msg2[10];
int samples = 0;
int val = 0;
int status = 1;
uint16_t xorResult = 0;
int trigcounter = 0;
enum triggerStates{triggerState, postTrigger, preTrigger};
enum triggerStates state;
int counter = 0;
uint16_t triggerPeriod = 0x0000;
/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
uint16_t logicBuffer[20];
/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */
uint16_t BIT0  = 0x0001;
uint16_t BIT1  = 0x0002;
uint16_t BIT2  = 0x0004;
uint16_t BIT3  = 0x0008;
uint16_t BIT4  = 0x0010;
uint16_t BIT5  = 0x0020;
uint16_t BIT6  = 0x0040;
uint16_t BIT7  = 0x0080;
uint16_t BIT8  = 0x0100;
uint16_t BIT9  = 0x0200;
uint16_t BIT10 = 0x0400;
uint16_t BIT11 = 0x0800;
uint16_t BIT12 = 0x1000;
uint16_t BIT13 = 0x2000;
uint16_t BIT14 = 0x4000;
uint16_t BIT15 = 0x8000;
/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
TIM_HandleTypeDef htim1;
TIM_HandleTypeDef htim16;
DMA_HandleTypeDef hdma_tim1_up;

/* USER CODE BEGIN PV */

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_DMA_Init(void);
static void MX_TIM16_Init(void);
static void MX_TIM1_Init(int period);
void Process_USB_Command(char *cmd);
//static void MX_TIM16_Init(void);

/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{
  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_DMA_Init();
  MX_USB_DEVICE_Init();
  MX_TIM16_Init();
  MX_TIM1_Init(period);
 // MX_TIM1_Init(0, 79);  // Initial setup for 1 MHz sampling rate
 // Start_TIM1_DMA();
 // MX_TIM16_Init();

  /* USER CODE BEGIN 2 */
//  HAL_TIM_Base_Start(&htim1);
//  HAL_DMA_Start_IT(&hdma_tim1_up, (uint32_t)&GPIOB->IDR, (uint32_t)buffer, BUFFER_SIZE);
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  state = preTrigger;

  //HAL_TIM_Base_Start_IT(&htim1);

  while (1)
  {
//	  if(n == 1024){
//		  n = 0;
//	  }


//	  if(trigger == 1 ){
//		  val = n;
//
//		  status = 1;
//
//	  }

    /* USER CODE END WHILE */
	  //if(trigger == 0 && status == 1){

	  switch(state){
	  	  case preTrigger:
	  		  if(status == 0){
	  			 HAL_TIM_Base_Start_IT(&htim1);

	  		  }
	  		  break;
	  	  case triggerState:

	  		  break;
	  	  case postTrigger:
	  		  trigger = 0;
	  		  sprintf(msg, "%hu\r\n", buffer[val++]);
	  		  CDC_Transmit_FS((uint8_t *)msg, strlen(msg));
	  		  HAL_Delay(1);


	  		  if(val == 300){
	  			  val = 0;
	  		  }
	  		 if(status == 0){
	  		 HAL_TIM_Base_Start_IT(&htim1);}
	  		  break;
	  }
    /* USER CODE BEGIN 3 */
  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};
  RCC_PeriphCLKInitTypeDef PeriphClkInit = {0};

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_ON;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLMUL = RCC_PLL_MUL9;
  RCC_OscInitStruct.PLL.PREDIV = RCC_PREDIV_DIV1;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
  {
    Error_Handler();
  }
  PeriphClkInit.PeriphClockSelection = RCC_PERIPHCLK_USB|RCC_PERIPHCLK_TIM1
                              |RCC_PERIPHCLK_TIM16;
  PeriphClkInit.USBClockSelection = RCC_USBCLKSOURCE_PLL_DIV1_5;
  PeriphClkInit.Tim1ClockSelection = RCC_TIM1CLK_HCLK;
  PeriphClkInit.Tim16ClockSelection = RCC_TIM16CLK_HCLK;
  if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit) != HAL_OK)
  {
    Error_Handler();
  }
}


void HAL_DMA_ConvCpltCallback(DMA_HandleTypeDef *hdma) {
	   if (hdma == &hdma_tim1_up) {
	        HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_5);  // Toggle GPIO pin (assuming PA5 is used)
	    }

}

void HAL_DMA_ErrorCallback(DMA_HandleTypeDef *hdma) {
    // Transfer error callback
}
/**
  * @brief TIM1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM1_Init(int period)
{

  /* USER CODE BEGIN TIM1_Init 0 */

  /* USER CODE END TIM1_Init 0 */

  TIM_ClockConfigTypeDef sClockSourceConfig = {0};
  TIM_MasterConfigTypeDef sMasterConfig = {0};
  TIM_OC_InitTypeDef sConfigOC = {0};
  TIM_BreakDeadTimeConfigTypeDef sBreakDeadTimeConfig = {0};

  /* USER CODE BEGIN TIM1_Init 1 */

  /* USER CODE END TIM1_Init 1 */
  htim1.Instance = TIM1;
  htim1.Init.Prescaler = 0;
  htim1.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim1.Init.Period = period-1;
  htim1.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim1.Init.RepetitionCounter = 0;
  htim1.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_Base_Init(&htim1) != HAL_OK)
  {
    Error_Handler();
  }
  sClockSourceConfig.ClockSource = TIM_CLOCKSOURCE_INTERNAL;
  if (HAL_TIM_ConfigClockSource(&htim1, &sClockSourceConfig) != HAL_OK)
  {
    Error_Handler();
  }
  if (HAL_TIM_PWM_Init(&htim1) != HAL_OK)
  {
    Error_Handler();
  }
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
  sMasterConfig.MasterOutputTrigger2 = TIM_TRGO2_RESET;
  sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim1, &sMasterConfig) != HAL_OK)
  {
    Error_Handler();
  }
  sConfigOC.OCMode = TIM_OCMODE_PWM1;
  sConfigOC.Pulse = 10;
  sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
  sConfigOC.OCNPolarity = TIM_OCNPOLARITY_HIGH;
  sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;
  sConfigOC.OCIdleState = TIM_OCIDLESTATE_RESET;
  sConfigOC.OCNIdleState = TIM_OCNIDLESTATE_RESET;
  if (HAL_TIM_PWM_ConfigChannel(&htim1, &sConfigOC, TIM_CHANNEL_1) != HAL_OK)
  {
    Error_Handler();
  }
  sBreakDeadTimeConfig.OffStateRunMode = TIM_OSSR_DISABLE;
  sBreakDeadTimeConfig.OffStateIDLEMode = TIM_OSSI_DISABLE;
  sBreakDeadTimeConfig.LockLevel = TIM_LOCKLEVEL_OFF;
  sBreakDeadTimeConfig.DeadTime = 0;
  sBreakDeadTimeConfig.BreakState = TIM_BREAK_DISABLE;
  sBreakDeadTimeConfig.BreakPolarity = TIM_BREAKPOLARITY_HIGH;
  sBreakDeadTimeConfig.BreakFilter = 0;
  sBreakDeadTimeConfig.Break2State = TIM_BREAK2_DISABLE;
  sBreakDeadTimeConfig.Break2Polarity = TIM_BREAK2POLARITY_HIGH;
  sBreakDeadTimeConfig.Break2Filter = 0;
  sBreakDeadTimeConfig.AutomaticOutput = TIM_AUTOMATICOUTPUT_DISABLE;
  if (HAL_TIMEx_ConfigBreakDeadTime(&htim1, &sBreakDeadTimeConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM1_Init 2 */

  /* USER CODE END TIM1_Init 2 */

  HAL_TIM_Base_Init(&htim1);

  // Configure DMA request on update event
  __HAL_TIM_ENABLE_DMA(&htim1, TIM_DMA_UPDATE);

}

/**
  * @brief TIM16 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM16_Init(void)
{

  /* USER CODE BEGIN TIM16_Init 0 */

  /* USER CODE END TIM16_Init 0 */

  /* USER CODE BEGIN TIM16_Init 1 */

  /* USER CODE END TIM16_Init 1 */
  htim16.Instance = TIM16;
  htim16.Init.Prescaler = 72-1;
  htim16.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim16.Init.Period = 6554-1;
  htim16.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim16.Init.RepetitionCounter = 0;
  htim16.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_Base_Init(&htim16) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM16_Init 2 */

  /* USER CODE END TIM16_Init 2 */

}

uint16_t trigPin;
uint16_t trigEdge; //Falling Edge
int triggerCount = 300;

void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim) {
	if (htim == &htim16) {
		trigger = 0;
		state = postTrigger;
		HAL_TIM_Base_Stop(&htim1);
		HAL_TIM_Base_Stop(&htim16);
	}
	if (htim == &htim1) {
//		if (trigger){
//			counter++;
//			if (counter == triggerCount){
//				state = postTrigger;
//				HAL_TIM_Base_Stop(&htim1);
//			}
//		}
		if(!trigger) {
			xorResult = GPIOB->IDR^buffer[bufferPointer];
			uint16_t trigPinCheck = xorResult & trigPin;
			uint16_t trigEdgeCheck = ~(buffer[bufferPointer]^trigEdge);
			trigger = (trigPinCheck & trigEdgeCheck) > 0;
			if (trigger){
				//start trigger timer
//				counter = 0;
				state = triggerState;
				HAL_TIM_Base_Start_IT(&htim16);
			}
		}

		//add 8 bit logic input to buffer
		buffer[bufferPointer] = GPIOB->IDR;
		//increments pointer with circular logic using logic gates
		bufferPointer++;
		bufferPointer &= 0x03FF;
//			if (bufferPointer > 1024){ // we can use and with 10 bits to with 0x03FF
//				bufferPointer = 0;
//			}
	}
}




/**
  * Enable DMA controller clock
  */
static void MX_DMA_Init(void)
{

  /* DMA controller clock enable */
  __HAL_RCC_DMA1_CLK_ENABLE();

  	  hdma_tim1_up.Instance = DMA1_Channel5;
      hdma_tim1_up.Init.Direction = DMA_PERIPH_TO_MEMORY;
      hdma_tim1_up.Init.PeriphInc = DMA_PINC_DISABLE;
      hdma_tim1_up.Init.MemInc = DMA_MINC_ENABLE;
      hdma_tim1_up.Init.PeriphDataAlignment = DMA_PDATAALIGN_HALFWORD;
      hdma_tim1_up.Init.MemDataAlignment = DMA_MDATAALIGN_HALFWORD;
      hdma_tim1_up.Init.Mode = DMA_CIRCULAR;
      hdma_tim1_up.Init.Priority = DMA_PRIORITY_LOW;

      //HAL_DMA_Init(&hdma_tim1_up);

      if (HAL_DMA_Init(&hdma_tim1_up) != HAL_OK)
          {
              Error_Handler();
          }

      __HAL_LINKDMA(&htim1, hdma[TIM_DMA_ID_UPDATE], hdma_tim1_up);

  /* DMA interrupt init */
  /* DMA1_Channel5_IRQn interrupt configuration */
  HAL_NVIC_SetPriority(DMA1_Channel5_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(DMA1_Channel5_IRQn);

}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};
/* USER CODE BEGIN MX_GPIO_Init_1 */
/* USER CODE END MX_GPIO_Init_1 */

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOF_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_RESET);

  /*Configure GPIO pin : PA5 */
  GPIO_InitStruct.Pin = GPIO_PIN_5;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_PULLDOWN;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);




  /*Configure GPIO pins : PB0 PB1 PB2 PB10
                           PB11 PB12 PB13 PB14
                           PB15 PB3 PB4 PB5
                           PB6 PB7 PB8 PB9 */
  GPIO_InitStruct.Pin = GPIO_PIN_0|GPIO_PIN_1|GPIO_PIN_2|GPIO_PIN_10
                          |GPIO_PIN_11|GPIO_PIN_12|GPIO_PIN_13|GPIO_PIN_14
                          |GPIO_PIN_15|GPIO_PIN_3|GPIO_PIN_4|GPIO_PIN_5
                          |GPIO_PIN_6|GPIO_PIN_7|GPIO_PIN_8|GPIO_PIN_9;
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_PULLDOWN;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

/* USER CODE BEGIN MX_GPIO_Init_2 */
/* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */


uint8_t trigPIN[8]={0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80};
int Period_T1[10]={1000, 2000, 3000, 45000, 50000, 32000, 35000, 25000, 40000, 65536};

int command = 0;

void Process_USB_Command(char *cmd) {
	//if its command state, convert to integer and take in the command value
	//value state
	command = atoi(cmd);
		switch(command){
		case 0://start
			status = 0;
			break;
		case 1: //stop
			status = 1;
			break;
		case 2: //trigger Falling Edge
			trigEdge = 0x00;
		case 3: //trigger Rising Edge;
			trigEdge = 0x01;
			break;
		case 4: //trigger PIN from 0 to 7
			trigPin = trigPIN[0];
			break;
		case 5:
			trigPin = trigPIN[1];
			break;
		case 6:
			trigPin = trigPIN[2];
			break;
		case 7:
			trigPin = trigPIN[3];
			break;
		case 8:
			trigPin = trigPIN[4];
			break;
		case 9:
			trigPin = trigPIN[5];
			break;
		case 10:
			trigPin = trigPIN[6];
			break;
		case 11:
			trigPin = trigPIN[7];
			break;
		case 12:
			trigPin = trigPIN[8];
			break;
		case 13:
			change_period(Period_T1[0]);

			break;
		case 14:
			change_period(Period_T1[1]);

			break;
		case 15:
			change_period(Period_T1[2]);

			break;
		case 16:
			change_period(Period_T1[3]);

			break;
		case 17:
			change_period(Period_T1[4]);

			break;
		case 18:
			change_period(Period_T1[5]);

			break;
			
		case 19:
			change_period(Period_T1[6]);

			break;
		case 20:
			change_period(Period_T1[7]);

			break;
			
		case 21:
			change_period(Period_T1[8]);

			break;
		case 22:
			change_period(Period_T1[9]);

			break;
		case 23:
			triggerPeriod ^= BIT0;
			change_period16(triggerPeriod);
			break;
		case 24:
			triggerPeriod ^= BIT1;
			change_period16(triggerPeriod);
			break;
		case 25:
			triggerPeriod ^= BIT2;
			change_period16(triggerPeriod);
			break;
		case 26:
			triggerPeriod ^= BIT3;
			change_period16(triggerPeriod);
			break;
		case 27:
			triggerPeriod ^= BIT4;
			change_period16(triggerPeriod);
			break;
		case 28:
			triggerPeriod ^= BIT5;
			change_period16(triggerPeriod);
			break;
		case 29:
			triggerPeriod ^= BIT6;
			change_period16(triggerPeriod);
			break;
		case 30:
			triggerPeriod ^= BIT7;
			change_period16(triggerPeriod);
			break;
		case 31:
			triggerPeriod ^= BIT8;
			change_period16(triggerPeriod);
			break;
		case 32:
			triggerPeriod ^= BIT9;
			change_period16(triggerPeriod);
			break;
		case 33:
			triggerPeriod ^= BIT10;
			change_period16(triggerPeriod);
			break;
		case 34:
			triggerPeriod ^= BIT11;
			change_period16(triggerPeriod);
			break;
		case 35:
			triggerPeriod ^= BIT12;
			change_period16(triggerPeriod);
			break;
		case 36:
			triggerPeriod ^= BIT13;
			change_period16(triggerPeriod);
			break;
		case 37:
			triggerPeriod ^= BIT14;
			change_period16(triggerPeriod);
			break;
		case 38:
			triggerPeriod ^= BIT15;
			change_period16(triggerPeriod);
			break;

		}		
	}
	//command state


//	int new_rate = 0;
//
//
//    if(command == 0){HAL_TIM_Base_Start_IT(&htim1);}
//
//    else if(command == 1){status = 1;}
//
//    else if(new_rate ==2){
//    	 trigEdge = 0x00;
//    }
//    else if(new_rate ==3){
//    	 trigEdge = 0x01;
//    }
//
//    else if(new_rate ==4){
//    	 trigPin = 000;
//    }
//
//    else {
//        // Handle invalid rate input (optional)
//    }

void change_period(int period){

	HAL_TIM_Base_Stop(&htim1);
	
	MX_TIM1_Init(period);
	
	HAL_TIM_Base_Start_IT(&htim1);
}
void change_period16(uint16_t period){

	HAL_TIM_Base_Stop(&htim16);

	MX_TIM1_Init(period);
	
//	HAL_TIM_Base_Start_IT(&htim16);
}

/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}

#ifdef  USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
