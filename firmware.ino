/**
 * @file firmware.ino
 * @brief Sistema de Simulación de Riego Inteligente
 * 
 * Lógica del microcontrolador para el control automático de riego basado en umbrales
 * de humedad, temperatura y luz. Implementado con buenas prácticas educativas:
 * sin bloqueos (uso de millis()) y estructuración limpia por capas.
 * 
 * Matriz de Conexiones:
 * - A0: Sensor Higrómetro (Humedad del suelo)
 * - A1: Sensor de Temperatura (TMP36)
 * - A2: Sensor de Luz (LDR)
 * - D7: Módulo Relé para Bomba de Agua (Actuador de potencia)
 * - D8: LED Verde (Estado Óptimo: Humedad adecuada, bomba inactiva)
 * - D9: LED Rojo (Alerta / Bomba Encendida)
 * - A4 (SDA) / A5 (SCL): Pantalla LCD 16x2 (I2C)
 */

#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// --- DEFINICIÓN DE CONSTANTES ---
// Pines de Entradas Analógicas
const byte PIN_HIGROMETRO = A0;
const byte PIN_TMP36      = A1;
const byte PIN_LDR        = A2;

// Pines de Salidas Digitales
const byte PIN_RELE_BOMBA = 7;
const byte PIN_LED_VERDE  = 8;
const byte PIN_LED_ROJO   = 9;

// Umbrales de Humedad (%)
const int UMBRAL_HUMEDAD_MIN = 40; // Riego inicia por debajo de este valor
const int UMBRAL_HUMEDAD_OK  = 45; // Riego se detiene por encima de este valor (histéresis)

// Intervalos de Tiempo (milisegundos)
const unsigned long INTERVALO_LECTURA   = 500;  // Frecuencia de muestreo de sensores
const unsigned long INTERVALO_SERIAL    = 1000; // Frecuencia de envío de telemetría por puerto serie
const unsigned long INTERVALO_LCD       = 1000; // Frecuencia de actualización de la pantalla

// --- VARIABLES GLOBALES ---
// Dirección I2C típica para LCD 16x2: 0x27 o 0x3F. Se inicializa 16 columnas y 2 filas.
LiquidCrystal_I2C lcd(0x27, 16, 2);

// Variables de almacenamiento de telemetría
int humedadPorcentaje = 0;
float temperaturaC    = 0.0;
int luzPorcentaje     = 0;
bool bombaActiva      = false;

// Variables para control de tiempo (no bloqueante)
unsigned long ultimoTiempoLectura = 0;
unsigned long ultimoTiempoSerial  = 0;
unsigned long ultimoTiempoLCD     = 0;

// --- PROTOTIPOS DE FUNCIONES ---
void leerSensores();
void procesarLogica();
void actualizarActuadores();
void enviarTelemetriaSerial();
void actualizarLCD();

void setup() {
  // Inicialización de Puerto Serie para Sincronización con Dashboard
  Serial.begin(9600);
  
  // Configuración de Pines
  pinMode(PIN_RELE_BOMBA, OUTPUT);
  pinMode(PIN_LED_VERDE, OUTPUT);
  pinMode(PIN_LED_ROJO, OUTPUT);
  
  // Estado inicial seguro de actuadores
  digitalWrite(PIN_RELE_BOMBA, LOW);
  digitalWrite(PIN_LED_VERDE, LOW);
  digitalWrite(PIN_LED_ROJO, LOW);
  
  // Inicialización de la pantalla LCD con I2C
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("SISTEMA DE RIEGO");
  lcd.setCursor(0, 1);
  lcd.print("INICIALIZANDO...");
  delay(1000); // Retardo permitido únicamente en setup() para mostrar inicio
  lcd.clear();
}

void loop() {
  unsigned long tiempoActual = millis();

  // 1. Capa de Lectura de Entradas (Temporizador no bloqueante)
  if (tiempoActual - ultimoTiempoLectura >= INTERVALO_LECTURA) {
    leerSensores();
    ultimoTiempoLectura = tiempoActual;
  }

  // 2. Capa de Procesamiento Lógico y Decisiones
  procesarLogica();

  // 3. Capa de Activación de Actuadores y Salidas
  actualizarActuadores();

  // 4. Comunicaciones y Despliegue Visual (Temporizadores no bloqueantes)
  if (tiempoActual - ultimoTiempoLCD >= INTERVALO_LCD) {
    actualizarLCD();
    ultimoTiempoLCD = tiempoActual;
  }

  if (tiempoActual - ultimoTiempoSerial >= INTERVALO_SERIAL) {
    enviarTelemetriaSerial();
    ultimoTiempoSerial = tiempoActual;
  }
}

/**
 * @brief Capa de Lectura: Obtiene y procesa las señales de los sensores analógicos.
 */
void leerSensores() {
  // --- 1. Sensor de Humedad (Higrómetro en A0) ---
  // Rango de lectura: 0 (seco) a 1023 (agua pura). Map del voltaje a porcentaje.
  int valorHigrometro = analogRead(PIN_HIGROMETRO);
  humedadPorcentaje = map(valorHigrometro, 0, 1023, 0, 100);
  // Restringir el porcentaje entre 0 y 100
  humedadPorcentaje = constrain(humedadPorcentaje, 0, 100);

  // --- 2. Sensor de Temperatura (TMP36 en A1) ---
  // Resolución del ADC: 5.0V / 1024 niveles. El TMP36 tiene un offset de 0.5V.
  int valorTMP36 = analogRead(PIN_TMP36);
  float voltaje = (valorTMP36 * 5.0) / 1024.0;
  temperaturaC = (voltaje - 0.5) * 100.0;

  // --- 3. Sensor de Luz (LDR en A2) ---
  // Rango de lectura: 0 (máxima oscuridad) a 1023 (máxima luz).
  int valorLDR = analogRead(PIN_LDR);
  luzPorcentaje = map(valorLDR, 0, 1023, 0, 100);
  luzPorcentaje = constrain(luzPorcentaje, 0, 100);
}

/**
 * @brief Capa de Procesamiento: Aplica la lógica de umbrales con histéresis.
 */
void procesarLogica() {
  // Lógica con Histéresis:
  // Si la humedad cae por debajo de UMBRAL_HUMEDAD_MIN, encendemos la bomba.
  // La bomba permanecerá activa hasta que la humedad supere UMBRAL_HUMEDAD_OK.
  if (humedadPorcentaje < UMBRAL_HUMEDAD_MIN) {
    bombaActiva = true;
  } 
  else if (humedadPorcentaje >= UMBRAL_HUMEDAD_OK) {
    bombaActiva = false;
  }
}

/**
 * @brief Capa de Actuación: Modifica el estado físico/eléctrico de las salidas.
 */
void actualizarActuadores() {
  if (bombaActiva) {
    digitalWrite(PIN_RELE_BOMBA, HIGH); // Conmuta el relé para encender el motor
    digitalWrite(PIN_LED_ROJO, HIGH);   // Enciende LED rojo de advertencia
    digitalWrite(PIN_LED_VERDE, LOW);   // Apaga LED verde
  } else {
    digitalWrite(PIN_RELE_BOMBA, LOW);  // Abre el relé para apagar el motor
    digitalWrite(PIN_LED_ROJO, LOW);    // Apaga LED rojo
    digitalWrite(PIN_LED_VERDE, HIGH);  // Enciende LED verde (sistema óptimo)
  }
}

/**
 * @brief Capa de Despliegue Local: Imprime el estado del sistema en la pantalla LCD.
 */
void actualizarLCD() {
  // Fila 0: Humedad y Temperatura
  lcd.setCursor(0, 0);
  lcd.print("H:");
  lcd.print(humedadPorcentaje);
  lcd.print("%  T:");
  lcd.print(temperaturaC, 1);
  lcd.print("C   "); // Espacios al final para limpiar residuos previos

  // Fila 1: Estado del Actuador
  lcd.setCursor(0, 1);
  if (bombaActiva) {
    lcd.print("RIEGO: ACTIVO   ");
  } else {
    lcd.print("RIEGO: APAGADO  ");
  }
}

/**
 * @brief Capa de Comunicaciones: Envía un reporte JSON estructurado por el puerto Serie.
 */
void enviarTelemetriaSerial() {
  // El formato JSON permite un parseo sumamente sencillo y robusto en el dashboard
  Serial.print("{\"hum\":");
  Serial.print(humedadPorcentaje);
  Serial.print(",\"temp\":");
  Serial.print(temperaturaC, 1);
  Serial.print(",\"ldr\":");
  Serial.print(luzPorcentaje);
  Serial.print(",\"bomba\":");
  Serial.print(bombaActiva ? 1 : 0);
  Serial.println("}");
}
