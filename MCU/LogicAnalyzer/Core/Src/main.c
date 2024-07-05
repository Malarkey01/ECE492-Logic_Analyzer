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
uint8_t Buff[10];
int trigger = 0;
char msg[10];
int check = 0;
int val = 0;
int status = 0;
int trigcounter = 0;
/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
uint16_t logicBuffer[20];
/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

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
//static void MX_TIM16_Init(void);
static void MX_TIM1_Init(uint32_t prescaler, uint32_t period);
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

	int n = 0;
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
  //MX_TIM16_Init();
  //MX_TIM1_Init();
  MX_TIM1_Init(0, 79);  // Initial setup for 1 MHz sampling rate
  Start_TIM1_DMA();
  /* USER CODE BEGIN 2 */
//  HAL_TIM_Base_Start(&htim1);
//  HAL_DMA_Start_IT(&hdma_tim1_up, (uint32_t)&GPIOB->IDR, (uint32_t)buffer, BUFFER_SIZE);
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
	  if(n == 1024){
		  n = 0;
	  }


	  if(trigger == 1 ){
		  val = n;

		  status = 1;

	  }

    /* USER CODE END WHILE */
	  if(trigger == 0 && status == 1){
	  sprintf(msg, "%hu\r\n", buffer[val]);
	  CDC_Transmit_FS((uint8_t *)msg, strlen(msg));
	  HAL_Delay(100);
	  val++;

	  if(val == 1024){
		  val = n;
	  }
	  }
	  else{
	  HAL_Delay(1);
	  n++;
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
static void MX_TIM1_Init(uint32_t prescaler, uint32_t period)
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
  htim1.Init.Prescaler = prescaler;
  htim1.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim1.Init.Period = period;
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
  sConfigOC.Pulse = 0;
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
//static void MX_TIM16_Init(void)
//{
//
//  /* USER CODE BEGIN TIM16_Init 0 */
//
//  /* USER CODE END TIM16_Init 0 */
//
//  /* USER CODE BEGIN TIM16_Init 1 */
//
//  /* USER CODE END TIM16_Init 1 */
//  htim16.Instance = TIM16;
//  htim16.Init.Prescaler = 72-1;
//  htim16.Init.CounterMode = TIM_COUNTERMODE_UP;
//  htim16.Init.Period = 1000-1;
//  htim16.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
//  htim16.Init.RepetitionCounter = 0;
//  htim16.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
//  if (HAL_TIM_Base_Init(&htim16) != HAL_OK)
//  {
//    Error_Handler();
//  }
//  /* USER CODE BEGIN TIM16_Init 2 */
//
//  /* USER CODE END TIM16_Init 2 */
//
//}


void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim) {
    if (htim == &htim1) {
        HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_5);  // Toggle GPIO pin (assuming PA5 is used)
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

      HAL_DMA_Init(&hdma_tim1_up);

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
  GPIO_InitStruct.Pull = GPIO_NOPULL;
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

void Start_TIM1_DMA(void) {
    HAL_TIM_Base_Start_IT(&htim1);
    HAL_DMA_Start_IT(&hdma_tim1_up, (uint32_t)&GPIOB->IDR, (uint32_t)buffer, BUFFER_SIZE);
}

void Stop_TIM1_DMA(void) {
    HAL_TIM_Base_Stop(&htim1);
    HAL_DMA_Abort(&hdma_tim1_up);
}

void Change_Sampling_Rate(uint32_t new_rate) {
    uint32_t prescaler = 0;  // Prescaler value set to 0 for high frequencies
    uint32_t period = (80000000 / (prescaler + 1) / new_rate) - 1;

    Stop_TIM1_DMA();
    MX_TIM1_Init(prescaler, period);
    Start_TIM1_DMA();
}

void Process_USB_Command(char *cmd) {
    uint32_t new_rate = atoi(cmd);  // Convert command string to integer
    if (new_rate == 1) {
    	check = 1;
    	Change_Sampling_Rate(100000);
        //Change_Sampling_Rate(new_rate);
    }
    else if(new_rate == 2){
    	check = 2;
    	Change_Sampling_Rate(200000);
    }
    else if(new_rate == 3){
    	Change_Sampling_Rate(300000);
    	check = 3;
    }
    else if(new_rate == 4){
    	Change_Sampling_Rate(400000);
    	check = 4;
    }

    else if(new_rate == 5){
    	Change_Sampling_Rate(500000);
    	check = 5;
    }

    else if(new_rate == 6){
    	trigger = 1;
    }
    else if(new_rate ==7){
    	trigger = 0;
    }

    else {
        // Handle invalid rate input (optional)
    }
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
