

**ESPECIFICACIÓN DE REQUERIMIENTOS DE SOFTWARE (ERS)**

Sistema de Simulación de Riego Inteligente con Microcontrolador y Dashboard Moderno

Para entornos educativos y de prototipado: Tinkercad / Proteus  
Fecha: Julio 2026  
Versión: 1.0

**Control de Versiones**

| Versión | Fecha | Descripción | Autor |
| :---- | :---- | :---- | :---- |
| 0.1 | 10/07/2026 | Borrador inicial de requerimientos de simulación y lógica. | Equipo de Desarrollo |
| 1.0 | 13/07/2026 | Versión base finalizada incorporando Tinkercad/Proteus e interfaz responsive. | Analista de Sistemas |

**1\. Introducción**

El presente documento detalla la Especificación de Requerimientos de Software (ERS) para el diseño, desarrollo e implementación de una aplicación y entorno virtualizados enfocados en la simulación de un sistema de riego inteligente basado en microcontroladores (Arduino o similares). El propósito primordial de esta herramienta es proveer un ecosistema de aprendizaje y experimentación seguro, accesible y económicamente viable para estudiantes y entusiastas de la ingeniería y la electrónica.

Mediante la integración de herramientas web embebidas o plataformas consolidadas como Tinkercad Circuits o Proteus, la aplicación resolverá la barrera de adquisición de hardware real en etapas tempranas. Esto mitiga directamente el riesgo de averías, cortocircuitos o quemaduras de componentes reales, facultando al estudiante a validar la lógica de programación, las conexiones de circuito y la integración con actuadores y pantallas antes del ensamblaje físico.

**1.1 Alcance del Sistema**

El sistema comprenderá dos grandes componentes acoplados:

* Capa de Simulación de Hardware: Replicará el comportamiento lógico-eléctrico de sensores de entorno (humedad de suelo, temperatura, luz) y actuadores (relés, motores de agua, indicadores LED y pantallas LCD).  
* Interfaz de Usuario (Dashboard Moderno): Una aplicación web responsive y de alta fidelidad estética que actuará como el centro de monitorización, control de variables lógicas y visualización de la telemetría simulada.

**2\. Descripción General del Sistema**

**2.1 Arquitectura Lógica de Hardware**

La arquitectura se basa en un lazo cerrado de control distribuido en tres niveles virtuales:

* Entrada (Sensores Virtuales): Módulos encargados de capturar las condiciones cambiantes del entorno, tales como la humedad de la tierra, la temperatura ambiente y los niveles de radiación solar / luz ambiental.  
* Procesamiento (Microcontrolador): Un Arduino Uno, Nano o similar virtualizado que ejecuta código en C++ (firmware). Se encargará de leer las señales analógicas y digitales de los sensores y aplicar los umbrales configurados.  
* Salida (Actuadores Virtuales): Componentes de retroalimentación física emulados. Si la humedad cae por debajo de un nivel específico, el microcontrolador conmuta un relé virtual, cerrando el circuito de potencia para activar un motor de corriente continua (que representa la bomba de agua física). Al mismo tiempo, se actualiza el estado de diodos LED de diagnóstico y se imprimen mensajes de estado en una pantalla LCD 16x2.

**2.2 Entorno de Simulación Recomendado**

Para garantizar la máxima accesibilidad y eliminar costos de licenciamiento en la etapa académica, el sistema está diseñado bajo el estándar de compatibilidad con Tinkercad Circuits (para un despliegue interactivo basado en navegador web sin instalaciones intermedias). Opcionalmente, se habilita el esquema de diseño para Proteus VSM si se requiere análisis detallado de osciloscopio o simulación avanzada de electrónica de potencia a nivel profesional.

**3\. Requerimientos Funcionales (RF)**

| ID | Nombre del Requerimiento | Descripción Detallada |
| :---- | :---- | :---- |
| RF-01 | Simulación de Entrada de Sensores | El sistema permitirá variar dinámicamente mediante potenciómetros o controles deslizantes los niveles de humedad de suelo, temperatura y luz solar. |
| RF-02 | Procesamiento y Lógica Automática | El microcontrolador evaluará el firmware precargado en tiempo real. Al detectar humedad de tierra inferior al límite crítico (ej. \< 40%), iniciará la secuencia de riego. |
| RF-03 | Control de Actuadores y Relé | Ante la señal de riego, el GPIO correspondiente activará un transistor/relé virtual que pondrá en marcha el motor de la bomba de agua. |
| RF-04 | Despliegue Visual en Pantalla LCD | La pantalla LCD 16x2 virtual mostrará cíclicamente los valores del entorno (Humedad %, Temp °C) y el estado del actuador ('RIEGO: ACTIVO' / 'RIEGO: APAGADO'). |
| RF-05 | Validación y Pruebas Antiquema | La plataforma integrará herramientas de depuración de código línea por línea y alertas de sobrecorriente o cortocircuitos lógicos en las conexiones. |
| RF-06 | Sincronización con Dashboard Moderno | La aplicación web responsive se conectará mediante una API o puerto serie emulado para reflejar los gráficos de simulación en una interfaz moderna. |

**4\. Requerimientos No Funcionales (RNF)**

**4.1 Usabilidad e Interfaz Moderna (Responsive)**

* RNF-01 (Diseño Adaptativo): La interfaz del Dashboard web debe ser totalmente responsive, adaptándose de forma fluida a pantallas de teléfonos inteligentes, tabletas y ordenadores de escritorio usando frameworks modernos como Tailwind CSS o Bootstrap 5\.  
* RNF-02 (Estética de Vanguardia): Implementación de un modo oscuro/claro nativo, tipografía limpia (interlineado controlado) y componentes visuales atractivos (tarjetas con sombras sutiles, microanimaciones en los motores simulados).

**4.2 Rendimiento y Compatibilidad**

* RNF-03 (Baja Latencia de Simulación): El desfase entre la alteración del sensor virtual y la respuesta del actuador/interfaz web no deberá superar los 200 milisegundos en condiciones óptimas de red.  
* RNF-04 (Accesibilidad Educativa): Cero necesidad de instalación de software pesado. La simulación central en Tinkercad debe ejecutarse al 100% sobre navegadores web comerciales modernos (Chrome, Firefox, Edge, Safari).

**5\. Matriz de Conexiones Lógicas (Esquema de Hardware)**

A continuación se define la asignación de pines y conexiones lógicas estructuradas para el código fuente del microcontrolador:

| Componente Virtual | Tipo de Señal | Pin Microcontrolador | Función / Descripción |
| :---- | :---- | :---- | :---- |
| Sensor Higrómetro (Suelo) | Analógica | Pin A0 | Mide el nivel de humedad en la tierra (0-1023). |
| Sensor TMP36 / LDR | Analógica | Pin A1 / Pin A2 | Lectura de temperatura ambiente y luminosidad. |
| Módulo Relé (Bomba de Agua) | Digital | Pin D7 | Salida alta (HIGH) para saturar el relé y encender el motor. |
| Pantalla LCD 16x2 (I2C) | Digital (Protocolo) | Pines A4 (SDA) / A5 (SCL) | Imprime métricas y alertas del sistema. |
| LEDs Indicadores (Verde/Rojo) | Digital | Pin D8 / Pin D9 | Verde: Humedad Óptima. Rojo: Alerta/Bomba Encendida. |

