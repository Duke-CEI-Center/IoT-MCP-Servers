"""
wiring.py

Pin assignments and reference voltage configuration for various sensors
and UART interface on the MicroPython platform.

This module centralizes all GPIO pin definitions so that hardware wiring
can be managed in one place. Update these values whenever you change
the physical connections on your board.

Constants defined:
  - MPU6050_SCL, MPU6050_SDA: I²C pins for the MPU6050 IMU sensor
  - KY035_ADC_PIN, KY035_DO_PIN: Analog and digital pins for the KY-035 sound sensor
  - KY026_ADC_PIN, KY026_DO_PIN: Analog and digital pins for the KY-026 light sensor
  - LM35_ADC_PIN, LM35_DO_PIN: Analog and digital pins for the LM35 temperature sensor
  - DS18X20_PIN           : One-wire pin for the DS18x20 digital thermometer
  - DHT11_PIN             : Digital data pin for the DHT11 humidity & temperature sensor
  - V_REF                 : Reference voltage used by ADC converters
  - UART_TX, UART_RX      : UART transmit and receive pins for serial communication
"""

from machine import ADC

MPU6050_SCL   = 7
MPU6050_SDA   = 6
KY035_ADC_PIN = 19
KY035_DO_PIN  = 20
KY026_ADC_PIN = 3
KY026_DO_PIN  = 21
LM35_DO_PIN   = 6
LM35_ADC_PIN  = 5
DS18X20_PIN   = 5
DHT11_PIN     = 7
V_REF         = 3.3
UART_TX       = 38
UART_RX       = 39
HC_SR501_PIN  = 4
KY020_PIN     = 20
KY021_DO_PIN  = 2
KY021_AO_PIN  = 3
KY004_PIN     = 19
VS1838B_PIN   = 1
KY038_ADC_PIN = 6
KY038_DO_PIN  = 7
KY040_CLK_PIN = 1
KY040_DT_PIN  = 1
KY040_SW_PIN  = 1
DS1307RTC_SDA_PIN = 1
DS1307RTC_SCL_PIN = 1
DS1307RTC_I2C_FREQ= 1
DS1307RTC_SQW_PIN = 1
KY023_ADC_X_PIN = 19
KY023_ADC_Y_PIN = 20
KY023_SW_PIN = 21
ADC_ATTENUATION  = ADC.ATTN_11DB
NRF24_CE_PIN  = 1
NRF24_CSN_PIN = 1
NRF24_SPI_BUS = 1
UV_ADC_PIN    = 1
NRF24_SPI_BAUD= 10000000
KY037_ADC_PIN = 4
KY037_DO_PIN  = 5
HCSR04_TRIG   = 19
HCSR04_ECHO   = 20
KY036_ADC_PIN = 7
KY036_DO_PIN  = 6
SW420_PIN     = 5
KY010_PIN     = 4
BH1750_SCL_PIN= 1
BH1750_SDA_PIN= 1
PN532_SCL_PIN = 1
PN532_SDA_PIN = 1
PN532_RST_PIN = 1
GY302_SCL_PIN = 7
GY302_SDA_PIN = 6
WATER_SENSOR_PIN = 5
TTP223_PIN    = 20
KY018_PIN     = 19
HW080_ADC_PIN = 20
HW080_DO_PIN  = 19
VEML6075_SDA  = 7
VEML6075_SCL  = 6
LTR390_SDA    = 7
LTR390_SCL    = 6