---
trigger: always_on
---

Estructura de la Guía de Buenas Prácticas
Introducción y Propósito: Define los estándares de calidad requeridos para asegurar que el proyecto sea modular, escalable y fácilmente replicable en un entorno educativo.

Desarrollo de Firmware (C++ / Arduino):

Gestión del tiempo: Prohibición estricta del uso de delay() para evitar el bloqueo del hilo de ejecución del microcontrolador. Se promueve el uso de temporizadores no bloqueantes mediante millis().

Estructura limpia: Separación por capas (lectura de entradas analógicas, procesamiento lógico de umbrales y activación controlada de actuadores). Eliminación de "números mágicos" mediante el uso mandatorio de const byte o #define.

Simulación Antiquema en Tinkercad / Proteus:

Fidelidad eléctrica: Uso obligatorio de resistencias limitadoras (220Ω - 330Ω) en LEDs y resistencias de pull-up/pull-down para evitar estados flotantes.

Aislamiento de potencia: Buenas prácticas de acoplamiento del relé para aislar la lógica del microcontrolador (5V) de la carga inductiva y amperaje del motor DC (bomba de agua).

Desarrollo de Interfaz Web (Dashboard):

Enfoque Adaptativo (Responsive): Reglas de diseño Mobile-First utilizando frameworks como Tailwind CSS o Bootstrap 5 para garantizar una correcta visualización desde pantallas de 360px de ancho.

Jerarquía de Color y Estados: Uso de microanimaciones suaves y alertas visuales vectoriales (SVG) que representen de manera interactiva el encendido del motor y las variaciones críticas de la humedad.