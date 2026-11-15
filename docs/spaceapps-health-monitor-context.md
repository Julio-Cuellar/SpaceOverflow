# Contexto del proyecto: monitoreo de salud para astronautas (NASA Space Apps 2026)

> Documento de contexto para un agente de Claude Code. Resume todo lo decidido, investigado y propuesto hasta el 14 nov 2026, 14:22 (hora de Ciudad de México). La fuente viva del equipo es la página «spaceApps» en Notion; este archivo la consolida y corrige sus inconsistencias (ver sección 14).

## 0. Cómo usar este documento

**Reglas para el agente:**

1. Distingue siempre entre lo **decidido**, lo **investigado** (con fuente), lo **sugerido** (ideas del equipo o del asistente, no cerradas) y lo **no verificado**. Cada sección lo marca.
2. No inventes umbrales médicos. Todo valor que no tenga fuente verificada en la sección 5 se escribe como **parámetro de demostración** y se etiqueta así en el código y en la interfaz.
3. No tomes decisiones de la sección 12 (preguntas abiertas) sin preguntar al usuario. Si el usuario no está, elige la opción más conservadora y déjala anotada.
4. El sistema es un **prototipo de apoyo a la decisión**, no un dispositivo médico ni una herramienta de diagnóstico. Eso debe verse en la interfaz y en el README.
5. El usuario habla español. Los textos de interfaz y documentación, salvo que se indique otra cosa, van en español. Pregunta si hace falta una versión en inglés para el jurado.

**Leyenda de estado usada en todo el documento:**

| Marca | Significado |
| --- | --- |
| `DECIDIDO` | El usuario lo confirmó. |
| `VERIFICADO` | Leído directamente en un documento NASA citado en este archivo. |
| `TB` | Leído en un Technical Brief (OCHMO), documento de referencia derivado de la norma, «for reference only». |
| `SUGERIDO` | Idea discutida pero no cerrada. |
| `DEMO` | Valor inventado o supuesto para la demostración. Debe etiquetarse como tal. |
| `NO VERIFICADO` | Dicho en la conversación o encontrado en búsquedas, sin haber abierto la fuente. |

---

## 1. El hackathon y el reto

- **Evento:** NASA International Space Apps Challenge 2026, tema «The Next Frontier». Fechas: **14 y 15 de noviembre de 2026**, 48 horas.
- **Reto elegido:** *Create Health Monitoring Software for Astronauts on Space Missions*. Temas: Exploración humana, Software, Exploración espacial. Dificultad indicada por organizadores locales: intermedia.
- **Texto oficial (resumen de la ficha, citado por una página de evento local):**
  - *Problema:* las misiones largas exponen a los astronautas a radiación espacial, aislamiento y confinamiento, gravedad alterada y un entorno cerrado hostil. Eso puede traer cambios inmunes, pérdida ósea, eventos cardiovasculares y problemas de salud conductual. Los astronautas cargan con gran parte de la responsabilidad de detectar esos cambios en sí mismos.
  - *Objetivo:* construir software que reúna indicadores de salud y permita a los astronautas evaluar y actuar sobre el estado de su salud.
- **No se pudo leer la ficha oficial completa** (`https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/`): la herramienta de lectura la bloqueó. No se conocen sus recursos de datos ni sus criterios de evaluación oficiales. **Pendiente: que una persona la lea y la compare con este documento.**
- **Criterios de premios** (de un repositorio de terceros, `NO VERIFICADO`): mejor uso de la ciencia, mejor uso de los datos, mejor uso de la tecnología, entre otros.
- **Competencia:** al menos diez repositorios públicos de otros equipos resuelven este mismo reto. La mayoría es un panel con signos vitales simulados y alertas por umbral. Ver sección 11 para cómo diferenciarse.

---

## 2. Concepto del producto

**Idea central (`DECIDIDO`):** un sistema que cruza **sensores del cuerpo** con **sensores de la cabina** para generar alertas y medidas a activar, y que funciona **de forma autónoma a bordo**, sin depender del enlace con el centro de control.

- **Usuario principal:** el astronauta, no el centro de control. El centro de control es un observador secundario cuando hay conexión.
- **Sensores del cuerpo:** ritmo cardíaco, presión arterial, oxigenación en sangre (SpO₂), temperatura corporal, horas de sueño, estado de ánimo. El apunte manuscrito del equipo también menciona azúcar en sangre (ver sección 5.6 sobre su disponibilidad a bordo).
- **Sensores de la cabina:** oxígeno, CO₂, presión interna, y opcionalmente temperatura, humedad, ruido y radiación.
- **Alertas ejemplo mencionadas por el usuario:** oxígeno alto o bajo, CO₂ a cierto nivel, porcentaje del oxígeno total de la misión ya consumido, y activación de medidas.
- **Valor del cruce cuerpo-ambiente:** NASA advierte que muchos síntomas atribuidos al CO₂ también los causa el desplazamiento de fluidos en microgravedad, y que los sensores fijos no ven bolsas locales de CO₂. Cruzar datos permite decir «el origen probable es el aire, no el astronauta» o al revés. (`TB`, Technical Brief de CO₂.)

**Características deseadas por el equipo (apunte manuscrito, `DECIDIDO` como lista de deseos):**

- Gamificación para ayudar a los astronautas a completar tareas que apoyen su salud.
- Gráficas dinámicas con la evolución de los indicadores en el tiempo.
- Codificación por colores para interpretar la salud de un vistazo.
- Explicaciones sencillas de mediciones, indicadores y riesgos, porque los astronautas no saben todo sobre cómo evaluar su salud.
- Mostrar la información en distintos entornos: nave, estación, rover o base lunar o planetaria.
- Recordatorios que inciten a completar acciones de salud como parte de la rutina.

**Preguntas que la herramienta debe poder responder (del apunte manuscrito):**

1. ¿Qué mediciones se pueden realizar en el espacio?
2. ¿Por qué es necesario un examen?
3. ¿Cómo afectan los peligros de los vuelos espaciales a estos indicadores?
4. ¿Cuándo merece un resultado la atención de la tripulación o de los cirujanos de vuelo en Tierra?
5. ¿Qué acciones pueden prevenir una condición crítica?

**Marco científico (`VERIFICADO` como marco, tomado del Programa de Investigación Humana de NASA):** los cinco peligros del vuelo espacial: (1) radiación espacial, (2) aislamiento y confinamiento, (3) distancia de la Tierra, (4) campos gravitacionales, (5) entornos cerrados hostiles. Cada indicador de la herramienta conviene etiquetarlo con el peligro al que responde.

---

## 3. Arquitectura

### 3.1 Principio rector (`DECIDIDO`)

**Arquitectura hexagonal (puertos y adaptadores).** El núcleo del dominio no conoce sensores, documentos, voz ni modelos concretos. Todo lo que cambia entre demo, jurado y vuelo real es un adaptador intercambiable.

### 3.2 Núcleo del dominio (sin dependencias externas)

- Motor de reglas **determinista y auditable** que decide cuándo hay una alerta. **El modelo de lenguaje nunca decide la alerta.**
- Cálculo de magnitudes derivadas (por ejemplo PIO2, sección 5.2).
- Cruce cuerpo-ambiente.
- Línea base personal por astronauta y comparación relativa.
- Selección de recomendación y de medida a activar a partir del catálogo.

### 3.3 Puertos (interfaces) y adaptadores

| Puerto | Qué hace | Adaptadores previstos |
| --- | --- | --- |
| Entrada de sensores | Entrega lecturas con marca de tiempo | Simulador (con escenarios), reproducción de datos reales (RadLab) y, en teoría, sensores reales |
| Conocimiento | Responde «qué hacer en esta situación» con cita de la fuente | (a) Datos de demostración etiquetados como ficticios; (b) RAG sobre PDFs públicos de NASA |
| Voz de entrada | Convierte la voz del astronauta en texto | Whisper local; Alexa (solo demo) |
| Redacción / asistente | Explica la alerta en lenguaje natural usando solo lo recuperado | Ollama local orquestado por n8n |
| Enlace con Tierra | Sincroniza datos con el centro de control cuando hay conexión | Opcional; el sistema funciona igual sin él |
| Almacenamiento | Guarda lecturas, alertas y línea base | Por definir |

### 3.4 Flujo previsto (`SUGERIDO`, descrito por el usuario)

1. Los sensores y las reglas pasan primero por el **backend**.
2. Ante un evento, el backend se lo manda al **agente en n8n**.
3. El agente consulta el **RAG** con los PDFs de NASA.
4. Con lo recuperado, **Ollama** resume y devuelve la respuesta con su fuente.

Ollama solo usa el RAG como herramienta complementaria. Las reglas siguen decidiendo la alerta.

### 3.5 Modo autónomo local (`DECIDIDO` como idea, detalles abiertos)

- Todo vive en un equipo local a bordo: datos, reglas, PDFs indexados, modelo de lenguaje y transcripción.
- Si se corta el enlace con el centro de control, la tripulación sigue recibiendo alertas y recomendaciones con su fuente.
- Cuando vuelve el enlace, se sincroniza. Qué se sube y quién decide qué compartir está **abierto** (sección 12).
- Contexto de por qué importa: la demora de señal a Marte se citó en 3 a 22 minutos por trayecto (`NO VERIFICADO` con fuente primaria; viene de una lectura de un repositorio de otro equipo).

### 3.6 Voz (`DECIDIDO`)

- **Whisper local** como transcripción principal (corre sin internet).
- **Alexa** como adaptador temporal solo para la demostración, por si Whisper se traba. Alexa procesa la voz en la nube, así que **no es autónoma**; hay que decirlo con honestidad en la presentación. Requiere crear un skill y un endpoint público (por ejemplo con un túnel) que llegue al backend o a n8n. El skill en modo desarrollo corre solo en la cuenta del equipo, lo cual alcanza.
- Mostrar siempre lo transcrito para confirmar antes de actuar (Whisper puede fallar con términos médicos o ruido de cabina).
- **Una emergencia nunca debe depender de que el astronauta hable:** la alerta sale de los sensores.
- Plan B: entrada por texto escrito, por si falla el wifi del evento o el micrófono.
- Estimación de esfuerzo para Whisper (`NO VERIFICADO`, estimación general): una a dos horas para la primera transcripción conectada al backend, más una o dos de pruebas con ruido y términos médicos. Considerar una variante rápida como faster-whisper y un modelo pequeño si no hay tarjeta gráfica.

### 3.7 Perfiles de ejecución (`DECIDIDO`)

Son **perfiles de desarrollo** (configuraciones que se activan al arrancar), no perfiles de usuario. Se eligen con una **variable de entorno**:

| Valor | Voz | Para qué |
| --- | --- | --- |
| `dev1` | Whisper | Desarrollo |
| `dev2` | Alexa | Desarrollo, ruta de respaldo para la demo |
| `jurado` | Whisper | Ejecución limpia por parte del jurado |

- Que `dev1` y `jurado` usen lo mismo es **a propósito**: separa lo de desarrollo de lo de entrega y muestra orden. No hay diferencia técnica buscada entre ambos.
- El nombre de la variable y el valor por defecto **no están definidos**. Recomendación del asistente (`SUGERIDO`): que el valor por defecto sea `jurado`, porque funciona sin internet y sin Alexa, así que es lo más seguro si alguien arranca sin configurar nada.

### 3.8 Entrega para el jurado con Docker (`DECIDIDO` como idea, detalles abiertos)

El jurado revisará el código y ejecutará el programa. Para evitar el «en mi máquina sí funciona», se publicará una **imagen de Docker en Docker Hub**.

- Que la imagen arranque por defecto con el perfil `jurado` y que el perfil se pueda cambiar con la variable de entorno al correr el contenedor.
- Incluir lo necesario para funcionar **sin internet**: backend, base de reglas, PDFs de NASA ya indexados, modelo de Whisper.
- Ollama y su modelo ocupan mucho espacio: decidir si van en la misma imagen o en un contenedor aparte con Docker Compose, junto con n8n.
- README con el comando exacto para descargar y correr la imagen y el enlace al repositorio.
- Revisar: tamaño final de la imagen, ausencia de tarjeta gráfica en el equipo del jurado y acceso al micrófono desde el contenedor (suele dar problemas según el sistema operativo; la entrada por texto debe ser alternativa funcional).
- Probar el contenedor en otra computadora, sin internet, antes de entregar.

---

## 4. Datos y entradas que ve el centro de control

Cuando hay conexión, todo es visible desde el centro de control: signos vitales, ambiente de la cabina, radiación, sueño y alertas generadas. Qué se comparte realmente está abierto (sección 12).

Datos de sueño (`NO VERIFICADO` con enlaces concretos; las afirmaciones se guardaron en Notion tras una búsqueda hecha en una sesión de voz y no se conservaron las URL):

- Pulseras de actigrafía (Actiwatch Spectrum): miden movimiento y luz ambiente en la muñeca; estiman sueño y vigilia, no las fases.
- Estudio Standard Measures: cuestionario antes y después de dormir (calidad del sueño, ánimo, cohesión del equipo, desempeño).
- Los astronautas duermen en promedio unas seis horas en el espacio.
- **No se encontró** un compartimento de dormir que mida el sueño por sí solo. Un módulo de dormir con sensores de ruido, luz, temperatura y movimiento es **solo una idea a explorar** y debe presentarse como tal.
- Verificado en la norma (`VERIFICADO`): cuartos de tripulación con límite de ruido NC-40 en misiones de más de 30 días, y vibración durante el sueño por debajo de 0.01 g RMS por intervalo de 2 minutos.

---

## 5. Catálogo de datos y reglas con fuente

> Las **bandas de severidad** (verde, amarillo, rojo) son una **propuesta del equipo**. La norma solo da límites. Marca las bandas como tales en el código.

### 5.1 Documentos leídos y qué se obtuvo de cada uno

| Documento | Qué se leyó |
| --- | --- |
| NASA-STD-3001 Vol. 2 Rev F (`https://www.nasa.gov/wp-content/uploads/2025/05/nasa-std-3001-vol-2.pdf`) | Sección 6 (atmósfera, agua, acústica, vibración, radiación) y sección 7.1 hasta 7.1.3. Es un PDF de unos 937 mil caracteres; el resto no se leyó. |
| NASA-STD-3001 Vol. 1 Rev C (`https://www.nasa.gov/wp-content/uploads/2023/11/nasa-std-3001-vol-1-rev-c-with-signature.pdf`) | Secciones 3 y 4, incluida 4.8 (radiación). Termina en un apéndice truncado en la lectura. |
| OCHMO-TB-003 Atmósfera habitable | Leído completo en texto. Tabla 6.2-1 y figuras vienen como imagen y se completaron con Vol. 2. |
| OCHMO-TB-044 Operaciones médicas | Leído. No trae umbrales numéricos para software. |
| Checklist del botiquín médico | Leído. |
| OCHMO-TB-002 (ECLSS) y OCHMO-TB-004 (CO₂) | Leídos en una sesión anterior de voz. Sus valores se anotaron en Notion. |

**Corrección importante:** el Technical Brief ECLSS daba una presión mínima de cabina de 26.2 kPa. La norma vigente (Vol. 2 Rev F) dice **34.5 kPa**. Usa el valor de la norma.

### 5.2 Umbrales del ambiente (nivel 1, usar tal cual)

| Parámetro | Valor | Requisito | Fuente / estado | Uso sugerido |
| --- | --- | --- | --- | --- |
| ppCO₂ promedio de 1 h | ≤ 3 mmHg | V2 6004 | `VERIFICADO` | Rojo. Ventana móvil de 1 h |
| PIO2 normoxia | 145 a 155 mmHg | V2 6003, Tabla 6.2-1 | `VERIFICADO` | Verde |
| PIO2 hipoxia leve, límite inferior | 127 mmHg, indefinido con plan de monitoreo | Tabla 6.2-1 | `VERIFICADO` | Amarillo bajo 145; rojo bajo 127 |
| PIO2 hipoxia, límite absoluto | 122 mmHg (promedio de 1 h) | Tabla 6.2-1 | `VERIFICADO` | Crítico |
| PIO2 hiperoxia indefinida, límite superior | 356 mmHg | Tabla 6.2-1 | `VERIFICADO` | Rojo por encima |
| PIO2 hiperoxia a corto plazo | 791 mmHg por 6 a 9 h | Tabla 6.2-1 | `VERIFICADO` | O₂ puro: 9 h si es la única exposición en 48 h, 6 h si en 24 h, máximo 5 días seguidos |
| Presión total | 34.5 < P ≤ 103 kPa (5.0 a 15.0 psia) | V2 6006 | `VERIFICADO` | Verde |
| Velocidad de cambio de presión | ≤ 13.5 psi/min si el cambio supera 1.0 psi; cambios ≤ 1.0 psi exentos | V2 6007 | `VERIFICADO` | Alerta de despresurización rápida |
| Gas diluyente | ≥ 30% | V2 6002 | `VERIFICADO` | Verificación de composición |
| Temperatura y humedad, límite de salud | 18 °C con 75% HR hasta 27 °C con 25% HR | V2 6012 | `VERIFICADO` como anclajes de la justificación; los puntos exactos de la figura no estaban en el texto | Rojo fuera |
| Temperatura y humedad, zona de desempeño | 20 a 25 °C y 30 a 60% HR | V2 6013 | Igual que el anterior | Amarillo fuera |
| Humedad promedio post-aterrizaje | 25–75% indefinido; 75–85% 24 h; 85–95% 12 h; > 95% 8 h | V2 6011, Tabla 6.2-2 | `VERIFICADO` | Solo tras quitarse el traje |
| Agua potable | Mínimo 2.5 L por tripulante al día | V2 6109 | `TB` (no re-verificado en Vol. 2) | Presupuesto |
| Frecuencia de muestreo | Atmósfera cada 5 s, presión cada 1 s, temperatura y humedad cada 1 min | V2 6001, Tabla 6.1-1 | `VERIFICADO` | Ritmo del simulador |
| Ruido, dosis 24 h | D ≤ 100 (equivale a 8 h a 75 dBA en órbita) | V2 6115 | `VERIFICADO` | Opcional |
| Ruido peligroso fuera de lanzamiento | < 85 dBA | V2 6077 | `VERIFICADO` | Opcional |
| Alarmas | < 95 dBA en la posición del receptor | V2 6081 | `VERIFICADO` | Opcional |
| Dormitorios (> 30 días) | NC-40 | V2 6079 | `VERIFICADO` | Opcional |
| Vibración durante el sueño | < 0.01 g RMS por intervalo de 2 min | V2 6092 | `VERIFICADO` | Opcional |
| Gases de combustión (rangos de **monitoreo**) | CO 5–1000 ppm; HCN, HCl, HF 2–50 ppm | Tabla 6.2-3 | `VERIFICADO` | Son rangos que el sensor debe cubrir, **no** límites de salud |

**Fórmula de oxígeno (`VERIFICADO`):** `PIO2 = (P_total − 47 mmHg) × fracción_O2`. El 47 mmHg es la presión de vapor de agua a 37 °C.

- El oxígeno debe evaluarse como **presión parcial**, no como porcentaje. Un porcentaje «normal» a baja presión puede ser hipoxia.
- Lo mismo aplica al CO₂: 3 mmHg equivale a 0.39% a nivel del mar (760 mmHg) pero a 0.71% a 56.5 kPa. Alertar «por porcentaje de CO₂» sin considerar la presión es incorrecto.
- Conversiones: 1 kPa = 7.50062 mmHg; 1 psi = 51.7149 mmHg.

**Vectores de prueba para el motor de reglas** (calculados por el asistente con la fórmula anterior):

| Entrada | Resultado esperado |
| --- | --- |
| 760 mmHg, 21% O₂ | PIO2 ≈ 149.7 mmHg, normoxia, verde |
| 760 mmHg, 18% O₂ | PIO2 ≈ 128.3 mmHg, por debajo de 145 (amarillo) y apenas sobre 127 |
| 56.5 kPa (423.8 mmHg), 34% O₂ | PIO2 ≈ 128.1 mmHg, amarillo, cerca del límite de 127 |
| ppCO₂ promedio de 1 h = 3.1 mmHg | Rojo |
| Presión 14.7 psia a 12.0 psia en 1 min (Δ 2.7 psi) | Dentro del límite de 13.5 psi/min; sin alerta por velocidad |
| Presión baja 14 psi en 0.5 min (28 psi/min) | Alerta de despresurización rápida |

### 5.3 Radiación (nivel 2, hay datos reales)

| Parámetro | Valor | Requisito |
| --- | --- | --- |
| Dosis de rayos cósmicos galácticos (GCR), espacio libre | < 1.3 mSv/día | V1 4033 |
| GCR en superficie planetaria | < 0.9 mSv/día | V1 4033 |
| Dosis efectiva de carrera | < 600 mSv | V1 4030 |
| Dosis por evento de partículas solares (espectro de referencia) | < 250 mSv | V1 4031 |
| Evento solar con más de 50 mSv proyectados | Exige monitores de área o personales | Tabla 6.8-1 |
| Más de 75 mSv acumulados en varias misiones | Exige monitoreo adicional | Tabla 6.8-1 |
| Tecnología nuclear | < 20 mSv por año de misión (≈ 0.05 mSv/día prorrateado) | V1 4032 |

Límites por órgano, Tabla 4.8-1 (`VERIFICADO`):

| Órgano | 30 días | 1 año | Carrera |
| --- | --- | --- | --- |
| Cristalino | 1,000 mGy-Eq | 2,000 mGy-Eq | 4,000 mGy-Eq |
| Piel | 1,500 mGy-Eq | 3,000 mGy-Eq | 6,000 mGy-Eq |
| Órganos formadores de sangre | 250 mGy-Eq | 500 mGy-Eq | no aplica |
| Sistema circulatorio | 250 mGy-Eq | 500 mGy-Eq | 1,000 mGy-Eq |
| SNC (hipocampo) | 500 mGy | 1,000 mGy | 1,500 mGy |
| SNC, Z ≥ 10 | no aplica | 100 mGy | 250 mGy |

- Estos límites dependen de modelos específicos de NASA (modelo Q y el espectro GCR del mínimo solar de 2009). **Los valores del prototipo serán aproximados** y así debe decirse.
- Qué se mide según la norma: monitoreo personal de GCR y monitoreo de eventos solares fuera de órbita baja.
- **Datos reales para el simulador:** NASA OSDR RadLab (`https://visualization.osdr.nasa.gov/radlab/`), que según un proyecto de otro equipo trae dosis absorbidas de los instrumentos DOSTEL (ISS), CRaTER (órbita lunar) y MSL-RAD (Marte); y NOAA SWPC para protones solares. **No se abrieron estos conjuntos de datos.** Verificar formato, licencia y fechas antes de usarlos.

### 5.4 Criterios del cuerpo relativos a la línea base (nivel 3)

Respaldan directamente la línea base personal por astronauta.

| Parámetro | Criterio | Requisito |
| --- | --- | --- |
| Capacidad aeróbica en misión | ≥ 80% del valor previo a la misión | V1 4003 |
| VO₂max absoluto | ≥ 32.9 mL/min/kg (EVA en microgravedad); ≥ 36.5 (EVA en superficie) | V1 4001, V1 4002 |
| Fuerza muscular en misión | ≥ 80% de la línea base | V1 4024 |
| Densidad ósea en misión | ≥ 95% de la previa en cadera y columna; ≥ 90% en cuello femoral | V1 4027 |
| Energía diaria | Promedio de 3,035 kcal por tripulante, o fórmula EER con factor de actividad 1.0–1.25; +200 kcal por hora de EVA | V2 7003, V2 7004 |
| Vitamina D | 25 µg al día | Tabla 7.1-2 |
| Sueño (valor por defecto configurable, no requisito) | Periodo de 8.5 h, más 2 h antes y 1.5 h después; mínimo circadiano entre la 1 y las 7 AM | V1 6001 (justificación) |

Fórmula EER (`VERIFICADO`, Tabla 7.1-1): hombres ≥ 19 años `662 − 9.53 × edad + FA × (15.9 × masa_kg + 539.6 × talla_m)`; mujeres ≥ 19 años `354 − 6.91 × edad + FA × (9.36 × masa_kg + 726 × talla_m)`.

Tabla 4.6-1, fuerza previa a la misión en múltiplos del peso corporal (lectura de columnas **inferida**, ambigua en el texto extraído): peso muerto mínimo 1.0, EVA en microgravedad 1.3, EVA en superficie 1.6; press de banca mínimo 0.7, 0.8 y 1.0. No usar sin revisar la tabla original.

### 5.5 Conocimiento cualitativo para el puerto de conocimiento (nivel 4)

- **CO₂, síntomas** (`TB`): dolor de cabeza entre 2.8 y 4.5 mmHg; fatiga, mal sueño y náuseas por encima de 4.5 mmHg. Para mantener el riesgo de dolor de cabeza bajo 1%, el promedio de 7 días debe ser menor a 2.5 mmHg. Apolo 13 llegó a 14.9 mmHg y bajó a 1 mmHg al improvisar filtros.
- **Hipoxia** (`VERIFICADO`, TB-003): cambios mentales a veces imperceptibles para el propio astronauta, visión reducida, fatiga, náuseas, dolor de cabeza, mareo, hiperventilación. Argumento a favor de que la alarma venga del sensor.
- **Hiperoxia:** reduce ventilación y frecuencia cardíaca; el tratamiento es bajar la ppO₂.
- **Enfermedad por descompresión:** tratamiento con recompresión y O₂ al 100%.
- **Mareo espacial:** unos 3 días en promedio (TB-044).
- **Rol del oficial médico (CMO):** dos por incremento; la decisión médica recae en el cirujano de vuelo en Tierra, con el grupo médico internacional en casos agudos. Sirve para definir cuándo escala una alerta a Tierra.
- **Medidas a activar:** el botiquín está organizado en 11 paquetes por color y contiene categorías de fármacos por condición (náuseas y mareo, sueño, dolor y fiebre, alergias, infecciones, respiratorio, gastrointestinal, mal de altura con acetazolamida, salud mental, cardíacos, emergencias). Sirve como catálogo de acciones, **no** como protocolo de qué dar y cuándo.
- **Mediciones a bordo, según el checklist del botiquín:** oxímetro de sangre, tensiómetro y monitor de presión, termómetro, estetoscopio, otoscopio, tonómetro, tiras de orina. El ritmo cardíaco continuo vendría de una pulsera o sensor (`NO VERIFICADO`).

### 5.6 Lo que NO está en los documentos públicos leídos

- **Umbrales de ritmo cardíaco, presión arterial y SpO₂.** Opciones: citar una escala externa como NEWS2 (la usan otros equipos; **no se verificó**) o etiquetarlos como `DEMO`.
- **Glucómetro y electrocardiógrafo:** el checklist leído no los lista. Afecta al «azúcar en sangre» del apunte del equipo.
- Valores críticos de hematología e inmunología, y límites de horas de trabajo y sueño: la norma dice que existen pero no los publica en el texto leído.
- Límites de CO₂ a 24 h, 7 y 1000 días en la norma: no aparecieron en la parte leída de Vol. 2. El de 2.5 mmHg a 7 días viene de un Technical Brief.
- Tabla 10.3-1 de Vol. 2 (alertas) no apareció en el tramo leído.
- Consumo de oxígeno por tripulante para el presupuesto de misión: **no confirmado**. La idea de «porcentaje de oxígeno gastado de la misión» necesita ese dato o un valor `DEMO`.
- Un árbol de decisión para fiebre u otros síntomas: no se encontró ninguno en lo abierto.

### 5.7 Estructura propuesta para el catálogo de reglas (`SUGERIDO`)

Un registro por regla, en JSON o YAML versionado, con estos campos: `id`, `parametro`, `operador`, `valor`, `unidad`, `ventana` (por ejemplo promedio de 1 h), `severidad`, `requisito_origen`, `documento`, `estado` (`VERIFICADO`, `TB` o `DEMO`), `peligro_hrp` (uno de los cinco) y `accion_sugerida`. La interfaz y las alertas deben mostrar `documento`, `requisito_origen` y `estado` para que cada alerta sea auditable.

```json
{
  "id": "env-co2-1h",
  "parametro": "ppCO2",
  "operador": ">",
  "valor": 3,
  "unidad": "mmHg",
  "ventana": "media_1h",
  "severidad": "rojo",
  "requisito_origen": "V2 6004",
  "documento": "NASA-STD-3001 Vol. 2 Rev F",
  "estado": "VERIFICADO",
  "peligro_hrp": "entornos_cerrados_hostiles",
  "accion_sugerida": "revisar_ventilacion_y_filtros"
}
```

---

## 6. Base de conocimiento (RAG)

### 6.1 Política de respuesta (`SUGERIDO`, alta prioridad)

- El modelo responde **solo** con pasajes recuperados y los cita. Si no hay pasaje que respalde la respuesta, dice que no tiene esa información. Nunca inventa protocolos médicos.
- Si falta un manual real para una situación, entra el adaptador de **datos de demostración**, y la respuesta lo dice explícitamente («dato de demostración, no de NASA»).
- Decisión abierta: ¿el RAG solo devuelve pasajes con su cita (más simple y auditable), o también redacta con Ollama? El equipo se inclina por usar Ollama como redactor.

### 6.2 Documentos candidatos y su estado

| Documento | URL | Estado |
| --- | --- | --- |
| NASA-STD-3001 Vol. 1 Rev C | `https://www.nasa.gov/wp-content/uploads/2023/11/nasa-std-3001-vol-1-rev-c-with-signature.pdf` | Leído en secciones 3 y 4 |
| NASA-STD-3001 Vol. 2 Rev F | `https://www.nasa.gov/wp-content/uploads/2025/05/nasa-std-3001-vol-2.pdf` | Leído en sección 6 y parte de 7.1 |
| TB-002 ECLSS | `https://www.nasa.gov/wp-content/uploads/2023/07/eclss-technical-brief-ochmo.pdf` | Leído |
| TB-003 Atmósfera habitable | `https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-003-habitable-atmosphere.pdf` | Leído |
| TB-004 CO₂ | `https://www.nasa.gov/wp-content/uploads/2023/03/co2-technical-brief-ochmo.pdf` | Leído |
| TB-044 Operaciones médicas | `https://www.nasa.gov/wp-content/uploads/2025/08/ochmo-tb-044-medical-operations.pdf` | Leído |
| Checklist del botiquín médico | `https://www.nasa.gov/wp-content/uploads/2015/03/medical_kit_checklist_-_full_release.pdf` | Leído |
| Human Integration Design Handbook | `https://www.nasa.gov/wp-content/uploads/2015/03/human_integration_design_handbook_revision_1.pdf` | **No abierto** |
| OCHMO-STD-100.1A (evaluaciones médicas) | `https://www.nasa.gov/wp-content/uploads/2023/04/ochmo-std-100.1a.pdf` | **No abierto** |
| Manual de emergencias médicas ISS (2016) | `https://www.governmentattic.org/19docs/NASA-ISSmedicalEmergManual_2016.pdf` | **No abierto.** Viene de una liberación por transparencia, no de un sitio oficial de NASA. Revisar licencia y vigencia antes de redistribuirlo en la imagen |

### 6.3 Notas prácticas para la ingesta (`SUGERIDO`)

- Algunas tablas de la norma son imágenes y no salen en el texto extraído (Tabla 6.2-1 en TB-003, figuras 6.2-2 y 6.2-3). Si se indexan PDFs, esas tablas necesitan transcripción manual o extracción visual; el catálogo de reglas de la sección 5 ya las contiene.
- Conservar por fragmento: documento, número de requisito, página y estado de verificación, para poder citar.
- Antes de redistribuir PDFs dentro de la imagen de Docker, confirmar que son de dominio público o que su licencia lo permite. Los documentos de nasa.gov marcados como de acceso público suelen serlo, pero **no se verificó la licencia de cada uno**.

---

## 7. Simulación de datos (`SUGERIDO`)

No hay signos vitales públicos en vuelo para entrenar ni validar. Por eso:

- Los datos del cuerpo serán **sintéticos** y deben etiquetarse como tales en código, interfaz y presentación.
- Respetar las frecuencias de la norma: atmósfera cada 5 s, presión cada 1 s, temperatura y humedad cada 1 min.
- Simular **escenarios** que demuestren el cruce cuerpo-ambiente: aumento lento de CO₂ con dolor de cabeza y cambio de frecuencia cardíaca; caída de presión con velocidad de cambio alta; hipoxia leve por baja presión total con porcentaje de O₂ aparentemente normal; evento de partículas solares con dosis creciente; deterioro del sueño en varios días contra la línea base; un caso en que el cuerpo cambia pero el ambiente está bien.
- Fuentes reales posibles: RadLab y NOAA SWPC para radiación; NASA OSDR (por ejemplo el dataset OSD-569 de conteo sanguíneo) para valores de laboratorio previos al vuelo. Otro equipo usó OSD-569 así; **no se abrió**.
- Decisión abierta: qué datos de sueño simular.

---

## 8. Asistente conversacional

- Modelo local con **Ollama** sobre **n8n** (`SUGERIDO`, descrito por el usuario). Probar un modelo pequeño en el equipo de la demo (el jurado puede no tener GPU).
- Ollama solo redacta y explica; las reglas deciden.
- Entrada por voz con Whisper local (sección 3.6). Salida como texto o con voz local (no decidido).
- Ya se descartó de momento usar APIs en la nube (OpenAI, Gemini, Anthropic) para el flujo principal, por la autonomía.

---

## 9. Restricciones de honestidad y seguridad

- Prototipo de apoyo a la decisión; **no es un dispositivo médico**; no diagnostica ni prescribe.
- Toda cifra sin fuente verificada se rotula `DEMO`.
- Las bandas de severidad son una propuesta del equipo.
- Las cifras de radiación dependen de modelos de NASA y serán aproximadas.
- Alexa no es autónoma: decirlo en la presentación.
- La alerta de emergencia sale de sensores, no de la voz.
- Si el sistema muestra una recomendación procedente de datos de demostración, debe decirlo.

---

## 10. Estado de decisiones

### 10.1 Decidido

- Reto elegido: monitoreo de salud para astronautas.
- Idea central: cruzar sensores del cuerpo con sensores de la cabina, con alertas y medidas.
- Arquitectura hexagonal con conocimiento intercambiable (demo / PDFs reales de NASA).
- Funcionamiento local y autónomo a bordo.
- Voz: Whisper local principal, Alexa solo como respaldo de demostración.
- Tres perfiles por variable de entorno: `dev1` (Whisper), `dev2` (Alexa), `jurado` (Whisper).
- Entrega con imagen de Docker en Docker Hub.
- Los bosquejos van como notas, sin etiquetar como «propuesta nuestra».

### 10.2 Descartado o aplazado

- La consulta sobre fiebre en vuelo fue solo una pregunta y **no se anotó en Notion** por indicación del usuario (ver sección 13).

---

## 11. Diferenciación frente a otros equipos

Ángulos que ya están en el diseño o la hacen posible:

- Cruce cuerpo-ambiente con atribución de causa probable.
- Línea base personal por astronauta (respaldada por criterios relativos de la norma).
- Reglas con fuente: cada alerta muestra documento, requisito y estado de verificación.
- Autonomía real: funciona sin conexión, con modelo y transcripción locales.
- Arquitectura que permite cambiar de datos de demostración a datos reales de NASA sin tocar el núcleo.
- Evaluar oxígeno y CO₂ por presión parcial, un detalle que casi nadie aplica.
- Entrega reproducible con Docker.

Por explorar: consentimiento del astronauta sobre qué se comparte con Tierra; módulo de dormir con sensores como concepto; gamificación y explicaciones didácticas.

---

## 12. Preguntas abiertas (no decidir sin consultar)

1. Nombre de la variable de entorno de perfil y valor por defecto (se sugiere `jurado`).
2. ¿El RAG solo devuelve pasajes con cita, o también redacta con Ollama?
3. Qué se sube a Tierra al reconectar y si el astronauta elige qué compartir.
4. Escenario de la demo: tránsito a Marte, base lunar, ISS u otro.
5. Qué medidas activa cada alerta.
6. Fuente de los umbrales de ritmo cardíaco, presión arterial y SpO₂.
7. Presupuesto de oxígeno de la misión: ¿se usa, y con qué consumo por tripulante?
8. ¿Ollama en la misma imagen o en un contenedor aparte con Docker Compose?
9. ¿Se usa JSON/YAML para el catálogo de reglas y quién lo mantiene?
10. **Stack tecnológico del backend, lenguaje, base de datos y interfaz: no se ha hablado.** Preguntar al usuario.
11. Tamaño y roles del equipo, y horas reales disponibles: no se conocen.
12. Qué datos de sueño simular.
13. Idioma de la interfaz y de la presentación al jurado.

---

## 13. Información no verificada fuera de Notion

Respuesta de una consulta de voz sobre fiebre en vuelo. **El asistente que escribe este documento no vio las fuentes**; las cifras se recogen aquí solo como pista para investigar, no como dato citable:

- Definición de fiebre del programa de estabilización de salud de la tripulación: 100.4 °F o más (unos 38 °C), proveniente del control previo al vuelo, no de un protocolo en órbita.
- Desregulación inmune durante el vuelo y reactivación de virus latentes (se mencionó que 9 de 17 astronautas estudiados eliminaron al menos un virus).
- Botiquín de la ISS con unos 190 medicamentos en dos kits.
- Reportes anecdóticos de que ciertos medicamentos son poco efectivos en vuelo, lo que justificaría que la herramienta registre si una medida funcionó.
- No se encontró un árbol de decisión para fiebre. El manual de emergencias médicas de la ISS, aún sin abrir, es el candidato más probable.

---

## 14. Inconsistencias conocidas en la página de Notion

Corregir o tener en cuenta:

1. La tabla de «Documentos candidatos» de la sección 5b sigue marcando como «No abierto» varios documentos que luego se leyeron (Vol. 1 secciones 3 y 4, Vol. 2 secciones 6 y 7.1, TB-003, TB-044, checklist del botiquín). El estado real está en la sección 6.2 de este archivo.
2. La sección 4 de Notion tiene dos bloques casi duplicados llamados «Segunda parte».
3. En la sección 5b, los límites ambientales aparecen con fuente «Technical Brief ECLSS» salvo la presión total; los valores de la norma se verificaron después en Vol. 2 (sección 5.2 de este archivo).
4. En 5b el «Pendiente» sobre leer secciones 3 y 4 de Vol. 1 ya está hecho.
5. En la sección 5d las notas de sueño citan fuentes NASA sin enlaces; ver sección 4 de este archivo.
6. En la sección 7 (pendientes), la casilla «Elegir qué PDFs públicos usar» está marcada hecha aunque quedan documentos por abrir.

---

## 15. Pendientes (copia de Notion, ordenados)

**Investigación**

- [ ] Leer la ficha oficial del reto y sus recursos
- [ ] Encontrar fuente para umbrales de signos vitales del cuerpo
- [ ] Abrir RadLab / OSDR y confirmar formato y licencia de los datos
- [ ] Abrir el manual de emergencias médicas de la ISS, el HIDH y OCHMO-STD-100.1A
- [ ] Decidir si se usa el presupuesto de oxígeno y con qué datos

**Diseño y decisiones**

- [ ] Definir alcance del MVP según el tiempo restante
- [ ] Repartir roles del equipo
- [ ] Decidir si el catálogo de reglas va en JSON y quién lo mantiene
- [ ] Confirmar si «RAC» era RAG y decidir si hay modelo de lenguaje o solo búsqueda de pasajes
- [ ] Decidir qué datos de sueño simular
- [ ] Elegir el nombre de la variable de entorno y su valor por defecto

**Implementación**

- [ ] Probar un modelo pequeño con Ollama en el equipo de la demo
- [ ] Probar Whisper local con ruido de fondo
- [ ] Armar el flujo en n8n: backend, agente, RAG y respuesta
- [ ] Crear el skill de Alexa y el túnel solo si Whisper se traba

**Entrega**

- [ ] Crear el Dockerfile y publicar la imagen en Docker Hub
- [ ] Decidir si Ollama va en la misma imagen o en un contenedor aparte con Docker Compose
- [ ] Probar el contenedor en otra computadora, sin internet, antes de entregar
- [ ] Escribir en el README el comando para descargar y ejecutar la imagen

**Hecho**

- [x] Definir los perfiles de desarrollo y cómo se cambia entre ellos
- [x] Primera selección de PDFs públicos de NASA y comprobación de descarga

---

## 16. Sugerencias del asistente (no decididas)

> Esta sección es opinión del asistente que redactó el documento. Ignórala si el usuario decide otra cosa.

**Orden de trabajo recomendado dado que el hackathon termina el 15 de noviembre:**

1. Núcleo del dominio y catálogo de reglas con los valores de la sección 5.2 y 5.3, con las pruebas de la tabla de vectores. Es lo más defendible ante un jurado y no depende de infraestructura.
2. Simulador de sensores con escenarios de la sección 7.
3. Interfaz con colores, tendencias y la explicación de cada alerta con su fuente.
4. Adaptador de conocimiento con datos de demostración, y después el de RAG sobre PDFs. Empezar por un puñado de fragmentos bien citados antes de indexar todo.
5. Whisper y Ollama detrás de sus puertos.
6. Docker, el perfil `jurado` y la prueba sin internet.
7. Alexa solo si sobra tiempo.

**Estructura de repositorio sugerida (hexagonal):**

```text
/domain          núcleo: reglas, cálculos, línea base, severidades
/ports           interfaces: sensores, conocimiento, voz, asistente, enlace, almacenamiento
/adapters
  /sensors       simulador, reproducción de RadLab
  /knowledge     demo, rag_nasa
  /voice         whisper_local, alexa
  /assistant     ollama_n8n
  /uplink        sincronización opcional
/rules           catálogo de reglas con fuente y estado
/data            simulaciones y datos reales descargados, con licencia
/profiles        configuración por perfil: dev1, dev2, jurado
/docker          Dockerfile y compose
/docs            README, notas de verificación
```

**Riesgos principales:** demasiadas piezas para 48 horas (n8n, Ollama, Whisper, Alexa, Docker); modelo local lento sin GPU; presentar valores `DEMO` como si fueran de NASA; redistribuir PDFs sin confirmar licencia; micrófono en Docker.

---

## 17. Fuentes

**Reto y contexto**

- Resumen del reto, Sonoma State: `https://edeon.sonoma.edu/nasaspaceapps-26/`
- NASA, anuncio de Space Apps 2026: `https://science.nasa.gov/universe/nasa-welcomes-all-ages-experience-levels-for-space-apps-challenge/`

**Documentos de NASA leídos**

- NASA-STD-3001 Vol. 1 Rev C: `https://www.nasa.gov/wp-content/uploads/2023/11/nasa-std-3001-vol-1-rev-c-with-signature.pdf`
- NASA-STD-3001 Vol. 2 Rev F: `https://www.nasa.gov/wp-content/uploads/2025/05/nasa-std-3001-vol-2.pdf`
- OCHMO-TB-002 ECLSS: `https://www.nasa.gov/wp-content/uploads/2023/07/eclss-technical-brief-ochmo.pdf`
- OCHMO-TB-003: `https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-003-habitable-atmosphere.pdf`
- OCHMO-TB-004 CO₂: `https://www.nasa.gov/wp-content/uploads/2023/03/co2-technical-brief-ochmo.pdf`
- OCHMO-TB-044: `https://www.nasa.gov/wp-content/uploads/2025/08/ochmo-tb-044-medical-operations.pdf`
- Checklist del botiquín: `https://www.nasa.gov/wp-content/uploads/2015/03/medical_kit_checklist_-_full_release.pdf`

**Proyectos de otros equipos consultados (referencia de enfoques)**

- AstroHealth: `https://github.com/Ridwanulkarim/nasa-challenge-Create-Health-Monitoring-Software-for-Astronauts-on-Space-Missions`
- AURORA (offline, RadLab, NOAA): `https://github.com/fabriciojunio/aurora-astronaut-health`
- Crew Health Monitor (reglas espaciales frente a terrestres, OSD-569): `https://github.com/AdityaK0804/Crew-Health-Monitor`

**Datos reales mencionados, sin abrir**

- NASA OSDR: `https://osdr.nasa.gov/`
- RadLab: `https://visualization.osdr.nasa.gov/radlab/`
- NOAA SWPC GOES (protones solares): sin URL verificada
