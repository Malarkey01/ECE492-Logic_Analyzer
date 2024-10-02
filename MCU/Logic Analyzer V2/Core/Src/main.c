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

/* USER CODE END PTD */
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
#define MAX_VALUES 2  // Number of values associated with each command
#define MAX_CMD_LENGTH 64  // Maximum command string length
/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */
#define USB_TX_BUFFER_SIZE 64  // Max USB packet size for Full Speed

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
TIM_HandleTypeDef htim2;
TIM_HandleTypeDef htim16;

/* USER CODE BEGIN PV */

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_TIM2_Init(uint32_t period);
static void MX_TIM16_Init(uint16_t period);
void Process_USB_Command(char *cmd);
void change_period2(uint32_t period);
void change_period16(uint16_t period);
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
  MX_TIM2_Init(0x00008CA0);
  MX_USB_DEVICE_Init();
  MX_TIM16_Init(0xFFFF);
  /* USER CODE BEGIN 2 */
  state = preTrigger;
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */


  while (1)
    {
      /* USER CODE END WHILE */
  	  switch(state){
  	  	  	  case preTrigger:
  	  	  		  break;
  	  	  	  case triggerState:

  	  	  		  break;
  	  	  	  case postTrigger:
  	  	  		 HAL_TIM_PWM_Stop(&htim2, TIM_CHANNEL_1);
  	  	  		 trigger = 0;
  	  	  		 //Send_Large_USB_Data((void*)buffer, 150 * sizeof(uint16_t));
  	  	  		 sprintf(msg, "%hu\r\n", buffer[val]);
  	  	  		 CDC_Transmit_FS((uint8_t *)msg, strlen(msg));
  	  	  		 HAL_Delay(1);
  	  	  		 val++;

  	  	  		 if(val == 1024){
  	  	  			 val = 0;

  	  	  			HAL_TIM_PWM_Start_IT(&htim2, TIM_CHANNEL_1);
  	  	  			state = preTrigger;

  	  	  		 }
  	  	  			break;

  //	  	  		 if(status == 0){
  //	  	  		 HAL_TIM_PWM_Start_IT(&htim2, TIM_CHANNEL_1);
  //	  	  		  break;

  	      /* USER CODE BEGIN 3 */
  	    }
  	    /* USER CODE END 3 */
  	  }
      /* USER CODE BEGIN 3 */
    }
    /* USER CODE END 3 */


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
  PeriphClkInit.PeriphClockSelection = RCC_PERIPHCLK_USB|RCC_PERIPHCLK_TIM16
                              |RCC_PERIPHCLK_TIM2;
  PeriphClkInit.USBClockSelection = RCC_USBCLKSOURCE_PLL_DIV1_5;
  PeriphClkInit.Tim16ClockSelection = RCC_TIM16CLK_HCLK;
  PeriphClkInit.Tim2ClockSelection = RCC_TIM2CLK_HCLK;
  if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief TIM2 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM2_Init(uint32_t period)
{

  /* USER CODE BEGIN TIM2_Init 0 */

  /* USER CODE END TIM2_Init 0 */

  TIM_MasterConfigTypeDef sMasterConfig = {0};
  TIM_OC_InitTypeDef sConfigOC = {0};

  /* USER CODE BEGIN TIM2_Init 1 */

  /* USER CODE END TIM2_Init 1 */
  htim2.Instance = TIM2;
  htim2.Init.Prescaler = 1;
  htim2.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim2.Init.Period = period-1;
  htim2.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim2.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_PWM_Init(&htim2) != HAL_OK)
  {
    Error_Handler();
  }
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
  sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim2, &sMasterConfig) != HAL_OK)
  {
    Error_Handler();
  }
  sConfigOC.OCMode = TIM_OCMODE_PWM1;
  sConfigOC.Pulse = 0;
  sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
  sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;
  if (HAL_TIM_PWM_ConfigChannel(&htim2, &sConfigOC, TIM_CHANNEL_1) != HAL_OK)
  {
    Error_Handler();
  }
  if (HAL_TIM_PWM_ConfigChannel(&htim2, &sConfigOC, TIM_CHANNEL_2) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM2_Init 2 */

  /* USER CODE END TIM2_Init 2 */

}

/**
  * @brief TIM16 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM16_Init(uint16_t period)
{

  /* USER CODE BEGIN TIM16_Init 0 */

  /* USER CODE END TIM16_Init 0 */

  TIM_OC_InitTypeDef sConfigOC = {0};
  TIM_BreakDeadTimeConfigTypeDef sBreakDeadTimeConfig = {0};

  /* USER CODE BEGIN TIM16_Init 1 */

  /* USER CODE END TIM16_Init 1 */
  htim16.Instance = TIM16;
  htim16.Init.Prescaler = 1;
  htim16.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim16.Init.Period = period-1;
  htim16.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim16.Init.RepetitionCounter = 0;
  htim16.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_Base_Init(&htim16) != HAL_OK)
  {
    Error_Handler();
  }
  if (HAL_TIM_PWM_Init(&htim16) != HAL_OK)
  {
    Error_Handler();
  }
  sConfigOC.OCMode = TIM_OCMODE_PWM1;
  sConfigOC.Pulse = 0;
  sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
  sConfigOC.OCNPolarity = TIM_OCNPOLARITY_HIGH;
  sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;
  sConfigOC.OCIdleState = TIM_OCIDLESTATE_RESET;
  sConfigOC.OCNIdleState = TIM_OCNIDLESTATE_RESET;
  if (HAL_TIM_PWM_ConfigChannel(&htim16, &sConfigOC, TIM_CHANNEL_1) != HAL_OK)
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
  sBreakDeadTimeConfig.AutomaticOutput = TIM_AUTOMATICOUTPUT_DISABLE;
  if (HAL_TIMEx_ConfigBreakDeadTime(&htim16, &sBreakDeadTimeConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM16_Init 2 */

  /* USER CODE END TIM16_Init 2 */

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
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOF_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(LD2_GPIO_Port, LD2_Pin, GPIO_PIN_RESET);

  /*Configure GPIO pin : B1_Pin */
  GPIO_InitStruct.Pin = B1_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_IT_FALLING;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(B1_GPIO_Port, &GPIO_InitStruct);

  /*Configure GPIO pin : LD2_Pin */
  GPIO_InitStruct.Pin = LD2_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(LD2_GPIO_Port, &GPIO_InitStruct);

  /*Configure GPIO pins : PB0 PB1 PB2 PB10
                           PB11 PB12 PB13 PB14
                           PB15 PB3 PB4 PB5
                           PB6 PB7 PB8 PB9 */
  GPIO_InitStruct.Pin = GPIO_PIN_0|GPIO_PIN_1|GPIO_PIN_2|GPIO_PIN_10
                          |GPIO_PIN_11|GPIO_PIN_12|GPIO_PIN_13|GPIO_PIN_14
                          |GPIO_PIN_15|GPIO_PIN_3|GPIO_PIN_4|GPIO_PIN_5
                          |GPIO_PIN_6|GPIO_PIN_7|GPIO_PIN_8|GPIO_PIN_9;
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

/* USER CODE BEGIN MX_GPIO_Init_2 */
/* USER CODE END MX_GPIO_Init_2 */
}

uint8_t trigPin = 0x01;
uint8_t trigEdge = 0x01; //Falling Edge
int triggerCount = 300;

void HAL_TIM_PWM_PulseFinishedCallback(TIM_HandleTypeDef *htim){
	if (htim->Channel == HAL_TIM_ACTIVE_CHANNEL_1) {
		if (trigger){
				counter++;
				if (counter == triggerCount){
					state = postTrigger;
					HAL_TIM_PWM_Stop(&htim2, TIM_CHANNEL_1);
				}
			}
			if(!trigger) {
				xorResult = GPIOB->IDR^buffer[bufferPointer];
				uint16_t trigPinCheck = xorResult & trigPin;
				uint16_t trigEdgeCheck = ~(buffer[bufferPointer]^trigEdge);
				trigger = (trigPinCheck & trigEdgeCheck) > 0;
				if (trigger){
					counter = 0;
					state = triggerState;
					//start timer 16
				}
			}

			//add 8 bit logic input to buffer
			buffer[bufferPointer] = GPIOB->IDR & 0xFFFF;
			//increments pointer with circular logic using logic gates
			bufferPointer++;
			bufferPointer &= 0x03FF;
	//			if (bufferPointer > 1024){ // we can use and with 10 bits to with 0x03FF
	//				bufferPointer = 0;
	//			}
	}



}
//void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim) {
////	if (htim == &htim16) {
////		trigger = 0;
////		state = postTrigger;
////		HAL_TIM_Base_Stop(&htim1);
////		HAL_TIM_Base_Stop(&htim16);
////	}
//	if (htim == &htim2) {
//		if (trigger){
//			counter++;
//			if (counter == triggerCount){
//				state = postTrigger;
//				HAL_TIM_PWM_Stop(&htim2, TIM_CHANNEL_1);
//			}
//		}
//		if(!trigger) {
//			xorResult = GPIOB->IDR^buffer[bufferPointer];
//			uint16_t trigPinCheck = xorResult & trigPin;
//			uint16_t trigEdgeCheck = ~(buffer[bufferPointer]^trigEdge);
//			trigger = (trigPinCheck & trigEdgeCheck) > 0;
//			if (trigger){
//				//start trigger timer
//				counter = 0;
//				//state = triggerState;
//				HAL_TIM_PWM_Start_IT(&htim2,TIM_CHANNEL_1);
//			}
//		}
//
//		//add 8 bit logic input to buffer
//		buffer[bufferPointer] = GPIOB->IDR;
//		//increments pointer with circular logic using logic gates
//		bufferPointer++;
//		bufferPointer &= 0x03FF;
////			if (bufferPointer > 1024){ // we can use and with 10 bits to with 0x03FF
////				bufferPointer = 0;
////			}
//	}
//}
uint8_t trigPIN[8]={0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80};
int Period_T1[10]={1000, 2000, 3000, 45000, 50000, 32000, 35000, 25000, 40000, 65536};
uint8_t buff[100] ;
int command = 0;
int temp = 0;
int commandValueFlag = 2; //0 is command, 1 is value 1, 2 is value 2, repeat
uint16_t period16 = 0x0000;
uint32_t period2 = 0x00000000;
uint16_t period2LowerHalf = 0x0000;
uint32_t period2UpperHalf = 0x00000000;
void Process_USB_Command(char *cmd) {


	commandValueFlag += 1;
	if (commandValueFlag == 3)
			commandValueFlag = 0;
	if (commandValueFlag == 0)
		command = atoi(cmd);
	else{
			switch(command){
			case 0://start
				HAL_TIM_PWM_Start_IT(&htim2, TIM_CHANNEL_1);
				state = preTrigger;
				break;
			case 1: //stop
				trigger = 0;
				HAL_TIM_PWM_Stop(&htim2, TIM_CHANNEL_1);
				break;
			case 2: //trigger Falling Edge
				trigEdge = atoi(cmd);
				break;
			case 3: //trigger Rising Edge;
				trigPin = atoi(cmd);
				break;
			case 4: //trigger PIN from 0 to 7
				period16 = period16 << 8;
				period16 |= atoi(cmd);
				change_period16(period16);
				break;

			case 5:
				period2UpperHalf = period2UpperHalf << 8;
				period2UpperHalf |= atoi(cmd);
				period2 &= 0x0000FFFF;
				period2 |= period2UpperHalf << 16;
				change_period2(period2);
				break;
			case 6:
				period2LowerHalf = period2LowerHalf << 8;
				period2LowerHalf |= atoi(cmd);
				period2 &= 0xFFFF0000;
				period2 |= period2LowerHalf;
				change_period2(period2);
				break;
			case 7:
				//trigPin = trigPIN[3];
				break;
			case 8:
				//trigPin = trigPIN[4];
				break;
			case 9:
				//trigPin = trigPIN[5];
				break;
			case 10:
				//trigPin = trigPIN[6];
				break;
			case 11:
				//trigPin = trigPIN[7];
				break;
			case 12:
				//trigPin = trigPIN[8];
				break;
			}
	}
	 memset(cmd, 0, strlen(cmd));  // Clear the command string//clear command

}
void change_period2(uint32_t period){
	HAL_TIM_PWM_Stop(&htim2, TIM_CHANNEL_1);

	MX_TIM2_Init(period);
}
void change_period16(uint16_t period){
	HAL_TIM_Base_Stop(&htim16);

	MX_TIM16_Init(period);
}
/* USER CODE BEGIN 4 */

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
