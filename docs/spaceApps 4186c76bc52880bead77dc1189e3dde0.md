# spaceApps

<aside>
🛰️

NASA Space Apps Challenge 2026 · 14–15 nov · Reto: **Create Health Monitoring Software for Astronauts on Space Missions**

</aside>

## 1. El reto

**Problema.** Las misiones largas exponen a los astronautas a radiación, aislamiento y confinamiento, gravedad alterada y un entorno cerrado hostil. Eso puede causar cambios inmunes, pérdida ósea, eventos cardiovasculares y problemas de salud conductual. Los propios astronautas tienen que detectar buena parte de esos cambios en sí mismos.

**Objetivo.** Construir software que reúna indicadores de salud y permita a los astronautas evaluar su estado y actuar en consecuencia.

Nota: no se pudo leer la ficha oficial completa (recursos y criterios de evaluación). Pendiente de verificar en [spaceappschallenge.org/2026/challenges/health-monitoring-software/](http://spaceappschallenge.org/2026/challenges/health-monitoring-software/)

## 2. Qué implica (análisis)

- El usuario es el astronauta, no el centro de control.
- Debe funcionar sin Tierra: la demora de señal a Marte es de 3 a 22 minutos por trayecto.
- Hay dos pasos distintos: evaluar (interpretar el dato) y actuar (protocolo, recomendación, alerta).
- Cubrir salud física y conductual.
- Casi no hay datos públicos de signos vitales en vuelo, así que habrá simulación. Hay que justificarla y etiquetar los umbrales sin fuente como parámetros de demostración.

**Marco científico:** los cinco peligros del HRP de NASA: radiación espacial, aislamiento y confinamiento, distancia de la Tierra, campos gravitacionales, ambientes hostiles o cerrados.

**Datos reales posibles:** NASA OSDR ([osdr.nasa.gov](http://osdr.nasa.gov), p. ej. OSD-569), RadLab, NOAA SWPC, NASA-STD-3001, escala NEWS2.

## 3. Competencia y diferenciación

Hay al menos diez repos públicos de otros equipos. La mayoría es un dashboard con signos vitales simulados y alertas por umbral.

Ángulos que sí diferencian:

- Línea base personal por astronauta
- Reglas adaptadas al espacio frente a rangos terrestres
- Explicabilidad: cada alerta con su razón y su fuente
- Consentimiento y privacidad sobre qué datos se comparten con Tierra
- Datos reales de NASA integrados, no solo citados
- Un usuario concreto y un escenario concreto

## 4. Nuestra propuesta

**Idea central (primera versión, 14 nov, por voz):** un sistema que combine sensores biométricos con sensores ambientales de la nave y genere alertas y medidas a activar.

- Biométricos: ritmo cardíaco, presión arterial, oxigenación en sangre.
- Ambientales: nivel de oxígeno, nivel de CO₂, presión interna de la cabina.
- Alertas posibles: oxígeno alto o bajo, CO₂ a cierto porcentaje, porcentaje de oxígeno total de la misión ya consumido.
- Cada alerta puede activar medidas.

Por definir: usuario concreto, escenario de demo, qué medidas se activan y cómo se cruzan los datos del cuerpo con los del ambiente.

**Segunda parte (14 nov, por voz): fuente de conocimiento y arquitectura**

- Usar datos públicos de NASA: los PDFs y manuales públicos que indican qué hacer en cada situación.
- Arquitectura hexagonal (puertos y adaptadores) para que la fuente de conocimiento sea intercambiable.
- Si no hay un manual a mano para una situación, se pueden usar datos de demostración inventados por el equipo.
- Esos datos de demostración se reemplazan después por datos reales de NASA sin tocar el núcleo del sistema.
- Los documentos reales alimentan un sistema de recuperación de información (en la nota por voz sonaba "RAC"; se entiende como RAG, por confirmar).

Boceto de la idea:

- Núcleo: reglas de alerta, cruce cuerpo-ambiente y recomendación.
- Puerto de entrada: sensores (simulados o reales).
- Puerto de conocimiento: "qué hacer en esta situación".
- Adaptador 1: datos de demostración, etiquetados como tales.
- Adaptador 2: PDFs públicos de NASA con recuperación de pasajes y cita de la fuente.

**Segunda parte (14 nov, por voz): datos públicos, RAG y arquitectura hexagonal**

- Usar documentos públicos de NASA (PDFs, manuales y protocolos) sobre qué hacer en cada situación, como base de conocimiento para un RAG.
- Arquitectura hexagonal (puertos y adaptadores): la fuente de conocimiento es un adaptador intercambiable.
- Si no hay manual real para una situación, se usa un adaptador con datos de demostración, claramente etiquetados como ficticios.
- Más adelante se puede cambiar por datos reales de NASA sin tocar el núcleo del sistema.

Por verificar: qué manuales médicos de NASA son realmente públicos y qué situaciones cubren.

## 5. Ideas discutidas

### Apunte manuscrito · 14 nov, 13:11 (PDF Notes_261114_131143)

**Planificación — problemática**

Construir software de monitoreo de salud de los astronautas en misiones espaciales. En misiones largas los astronautas no pueden depender del control en tierra, así que el astronauta debe detectar cambios en sí mismo.

**Cinco peligros de los vuelos espaciales**

1. Radiación espacial
2. Aislamiento y confinamiento
3. Distancia de la Tierra
4. Campos de gravedad
5. Entornos cerrados hostiles

**Estos peligros representan problemas de salud**

- Cambios en el sistema inmunológico
- Pérdida de densidad ósea
- Eventos cardiovasculares
- Nutrición inadecuada
- Condiciones de salud conductual

Los astronautas deben ser capaces de realizar evaluaciones de salud en sí mismos durante una misión, para prevenir y tratar problemas de salud que puedan surgir.

**Indicadores de salud útiles**

- Presión arterial
- Frecuencia cardíaca
- Azúcar en la sangre
- Temperatura corporal
- Horas de sueño
- Estado de ánimo

**Utilizar los recursos del Programa de Investigación Humana de la NASA**

Preguntas que la herramienta debe poder responder:

- ¿Qué mediciones se pueden realizar en el espacio?
- ¿Por qué es necesario un examen?
- ¿Cómo afectan los peligros de los vuelos espaciales a estos indicadores de salud?
- ¿Cuándo podría un resultado merecer la atención de la tripulación o de los cirujanos de vuelo en tierra?
- ¿Qué acciones se pueden tomar para prevenir una condición de salud crítica?

**A considerar**

- Proporcionar información de la salud de los astronautas en diferentes entornos: nave espacial, estación espacial, rover o una base en otro planeta o luna.
- Herramienta para incitar a los astronautas a tomar medidas o completar acciones específicas de vez en cuando como parte de la rutina de la misión.

**Incluir las siguientes características**

- Gamificación para ayudar a los astronautas a realizar tareas que apoyen su salud
- Gráficas dinámicas que muestren cambios en los indicadores de salud de los astronautas con el tiempo
- Codificación de colores que ayuden a la interpretación de salud de un vistazo

Los astronautas no saben todo sobre cómo evaluar su salud. La herramienta podría proporcionar instrucciones y explicaciones sencillas que cubran mediciones, indicadores de salud y riesgos.

## 5b. Fuentes de conocimiento (PDFs públicos de NASA)

Estas son las fuentes que alimentarían el puerto de conocimiento. Los límites de abajo se leyeron directamente en los Technical Briefs de OCHMO, que son documentos de referencia derivados de NASA-STD-3001 ("for reference only", no sustituyen la norma). Para citar en la presentación conviene confirmar cada valor en la norma completa.

### Límites ambientales verificados

| Parámetro | Límite | Requisito | Fuente |
| --- | --- | --- | --- |
| CO₂ (promedio de 1 hora) | No más de 3 mmHg de presión parcial | [V2 6004] | [Technical Brief CO₂](https://www.nasa.gov/wp-content/uploads/2023/03/co2-technical-brief-ochmo.pdf) |
| O₂ (presión parcial inspirada) | Rango de normoxia: 145 a 155 mmHg | [V2 6003] | [Technical Brief ECLSS](https://www.nasa.gov/wp-content/uploads/2023/07/eclss-technical-brief-ochmo.pdf) |
| Gas diluyente (nitrógeno) | Al menos 30% de la atmósfera | [V2 6002] | Technical Brief ECLSS |
| Presión total de cabina | Entre 34.5 y 103 kPa (5.0 a 15.0 psia), exposición indefinida. **Corregido:** el 26.2 kPa del Technical Brief ECLSS era de una revisión anterior; la norma Vol. 2 Rev F lo trae en 34.5 kPa | [V2 6006] | NASA-STD-3001 Vol. 2 Rev F |
| Velocidad de cambio de presión | Máximo 13.5 psi/min si el cambio supera 1.0 psi | [V2 6007] | Technical Brief ECLSS |
| Temperatura y humedad (límite de salud) | 18 °C con 75% de humedad hasta 27 °C con 25% | [V2 6012] | Technical Brief ECLSS |
| Temperatura y humedad (zona de desempeño) | 20 a 25 °C y 30 a 60% de humedad | [V2 6013] | Technical Brief ECLSS |
| Agua potable | Mínimo 2.5 L por tripulante al día | [V2 6109] | Technical Brief ECLSS |
| Alimentación | Promedio de 3,035 kcal por tripulante al día | [V2 7003] | Technical Brief ECLSS |

### Datos útiles para las alertas de CO₂

- Síntomas observados por nivel de CO₂: dolores de cabeza entre 2.8 y 4.5 mmHg, y fatiga, mal sueño y náuseas por encima de 4.5 mmHg.
- Para mantener el riesgo de dolor de cabeza por debajo de 1%, el promedio de 7 días debe estar por debajo de 2.5 mmHg.
- Nivel de referencia en la Tierra: el aire interior promedio tiene entre 0.08% y 0.1% de CO₂, es decir, 0.608 a 0.76 mmHg.
- Caso histórico: en el Apolo 13 el CO₂ llegó a 14.9 mmHg y bajó a 1 mmHg tras improvisar los filtros.
- Advertencia de NASA: muchos síntomas atribuidos al CO₂ también los causa el desplazamiento de fluidos en microgravedad, y los sensores fijos no ven las bolsas locales de CO₂. Esto justifica cruzar el ambiente con los datos del cuerpo.

### Requisitos que respaldan nuestra idea

- [V2 6021] La norma exige mostrar en tiempo real presión, humedad, temperatura, ppO₂ y ppCO₂.
- [V2 6022] La norma exige alertar a la tripulación, de forma local y remota, cuando esos parámetros salen de límites seguros.
- [V2 6001] La norma exige datos de monitoreo en formato compatible con análisis de tendencias.
- [V1 3003] Los programas deben ofrecer capacidades en misión para monitorear el bienestar fisiológico y psicosocial.
- [V1 3004] Los programas deben ofrecer capacidades y recursos para diagnosticar y tratar condiciones médicas posibles.

### Documentos candidatos para el puerto de conocimiento

| Documento | Para qué sirve | Estado |
| --- | --- | --- |
| [NASA-STD-3001 Vol. 1, Rev C](https://www.nasa.gov/wp-content/uploads/2023/11/nasa-std-3001-vol-1-rev-c-with-signature.pdf?emrc=6a7d82570f36c) | Salud de la tripulación: aptitud para el servicio, límites de exposición, atención médica. 86 páginas. | Abierto solo el índice y el alcance. Falta leer secciones 3 y 4. |
| [NASA-STD-3001 Vol. 2, Rev F](https://www.nasa.gov/wp-content/uploads/2025/05/nasa-std-3001-vol-2.pdf) | Límites ambientales y de hábitat. | No abierto completo. Los límites salieron de los Technical Briefs. |
| [Technical Brief ECLSS (OCHMO-TB-002)](https://www.nasa.gov/wp-content/uploads/2023/07/eclss-technical-brief-ochmo.pdf) | Resumen de atmósfera, agua y soporte vital. | Leído. |
| [Technical Brief CO₂ (OCHMO-TB-004)](https://www.nasa.gov/wp-content/uploads/2023/03/co2-technical-brief-ochmo.pdf) | Síntomas, niveles históricos y requisitos de CO₂. | Leído. |
| [Technical Brief Atmósfera habitable (OCHMO-TB-003)](https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-003-habitable-atmosphere.pdf) | Presión y composición de cabina. | No abierto. |
| [Technical Brief Operaciones médicas (OCHMO-TB-044)](https://www.nasa.gov/wp-content/uploads/2025/08/ochmo-tb-044-medical-operations.pdf) | Estructura de operaciones médicas de la ISS. | No abierto. |
| [Human Integration Design Handbook](https://www.nasa.gov/wp-content/uploads/2015/03/human_integration_design_handbook_revision_1.pdf) | Fundamento, historia y datos detrás de la norma. | No abierto. |
| [Checklist del botiquín médico](https://www.nasa.gov/wp-content/uploads/2015/03/medical_kit_checklist_-_full_release.pdf) | Medicamentos, efectos secundarios y ubicación. | No abierto. |
| [Manual de emergencias médicas ISS (2016)](https://www.governmentattic.org/19docs/NASA-ISSmedicalEmergManual_2016.pdf) | Procedimientos paso a paso. Viene de una liberación por transparencia, no de un sitio oficial de NASA. | No abierto. Revisar licencia y vigencia. |
| [OCHMO-STD-100.1A](https://www.nasa.gov/wp-content/uploads/2023/04/ochmo-std-100.1a.pdf) | Evaluaciones médicas y calendario de pruebas. | No abierto. |

### Pendientes de esta sección

- Los umbrales de signos vitales del cuerpo (ritmo cardíaco, presión arterial, oxigenación en sangre) no salieron de estos documentos. Hay que buscarlos en otra fuente o etiquetarlos como parámetros de demostración.
- Falta leer las secciones 3 y 4 del Volumen 1, que cubren atención médica en misión y límites de aptitud física.
- El presupuesto de oxígeno por misión puede calcularse con los datos del Technical Brief ECLSS (consumo de O₂ en reposo y con ejercicio por tripulante). Falta definir si lo usamos.

## 5c. Análisis: datos de mayor utilidad para el algoritmo

Leído el 14 nov directamente en NASA-STD-3001 Vol. 2 Rev F (sección 6 y sección 7.1 hasta 7.1.3; el resto del documento no se leyó), Vol. 1 Rev C (secciones 3 y 4, incluida 4.8 radiación), Technical Briefs OCHMO-TB-003 y TB-044, y el checklist del botiquín. Las bandas de severidad (verde, amarillo, rojo) son una propuesta del equipo; la norma solo da límites.

### Hallazgos que cambian el diseño

- **El oxígeno se mide como presión parcial, no como porcentaje.** La norma define PIO2 = (Presión total − 47 mmHg) × fracción de O₂. Con 14.7 psia y 21% de O₂ da unos 150 mmHg, dentro de la normoxia. Con cabina a menor presión, un porcentaje "normal" puede ser hipoxia. El algoritmo debe calcular PIO2 a partir de dos sensores (presión y % de O₂).
- **La norma pide justo lo que proponemos.** [V2 6020] registro continuo, [V2 6021] visualización en tiempo real, [V2 6022] alerta local y remota, [V2 6001] datos aptos para análisis de tendencias.
- **Los criterios de salud del cuerpo son relativos a la línea base de cada astronauta.** Respalda directamente la línea base personal.
- **Los umbrales de ritmo cardíaco, presión arterial y SpO₂ no están en estos documentos.** El botiquín sí incluye oxímetro de sangre, tensiómetro y termómetro, así que son mediciones reales a bordo. El checklist leído no lista glucómetro ni ECG, lo que afecta al "azúcar en sangre" de nuestro apunte.

### Nivel 1: umbrales duros del ambiente (usar tal cual)

| Parámetro | Valor | Requisito | Uso en el algoritmo |
| --- | --- | --- | --- |
| ppCO₂, promedio de 1 hora | ≤ 3 mmHg | [V2 6004] | Límite rojo. Ventana móvil de 1 h |
| PIO2 normoxia | 145 a 155 mmHg | [V2 6003], Tabla 6.2-1 | Rango verde |
| PIO2 hipoxia leve, límite inferior | 127 mmHg, indefinido con plan de monitoreo | Tabla 6.2-1 | Amarillo por debajo de 145, rojo por debajo de 127 |
| PIO2 hipoxia, límite absoluto | 122 mmHg (promedio de 1 h) | Tabla 6.2-1 | Crítico |
| PIO2 hiperoxia | 356 mmHg indefinido; 791 mmHg solo 6 a 9 h | Tabla 6.2-1 | Rojo por encima de 356. O₂ puro: 9 h máximo si es la única exposición en 48 h, 6 h si en 24 h, no más de 5 días seguidos |
| Presión total | 34.5 a 103 kPa | [V2 6006] | Rango verde |
| Velocidad de cambio de presión | ≤ 13.5 psi/min si el cambio supera 1.0 psi | [V2 6007] | Alerta de despresurización rápida |
| Gas diluyente | ≥ 30% | [V2 6002] | Verificación de composición |
| Temperatura y humedad | Límite de salud 18 °C con 75% HR hasta 27 °C con 25% HR; zona de desempeño 20 a 25 °C y 30 a 60% HR | [V2 6012] y [V2 6013] | Amarillo fuera de la zona de desempeño, rojo fuera del límite de salud. Los puntos exactos de la figura no están en el texto; son los anclajes de la justificación |
| Frecuencia de muestreo | Atmósfera cada 5 s, presión cada 1 s, temperatura y humedad cada 1 min | [V2 6001], Tabla 6.1-1 | Define el ritmo del simulador de sensores |
| Ruido | Dosis 24 h D ≤ 100 (8 h a 75 dBA en órbita); peligroso ≥ 85 dBA; alarmas < 95 dBA; dormitorios NC-40 | [V2 6115] [V2 6077] [V2 6081] [V2 6079] | Sensor opcional |
| Vibración durante el sueño | < 0.01 g RMS por intervalo de 2 min | [V2 6092] | Sensor opcional |
| Gases de combustión | Rangos de monitoreo: CO 5 a 1000 ppm, HCN, HCl, HF 2 a 50 ppm | Tabla 6.2-3 | Son rangos que el sensor debe cubrir, no límites de salud |

### Nivel 2: radiación (muy diferenciador, hay datos reales)

| Parámetro | Valor | Requisito |
| --- | --- | --- |
| Dosis GCR en espacio libre | < 1.3 mSv/día | [V1 4033] |
| Dosis GCR en superficie planetaria | < 0.9 mSv/día | [V1 4033] |
| Dosis efectiva de carrera | < 600 mSv | [V1 4030] |
| Dosis por evento de partículas solares | < 250 mSv | [V1 4031] |
| Más de 50 mSv por evento solar | Exige monitores de área o personales | Tabla 6.8-1 |
| Más de 75 mSv acumulados en varias misiones | Exige monitoreo adicional | Tabla 6.8-1 |
| Límites por órgano a 30 días, 1 año y carrera | Sangre: 250 y 500 mGy-Eq. Circulatorio: 250, 500 y 1,000. Cristalino: 1,000, 2,000 y 4,000. Piel: 1,500, 3,000 y 6,000. SNC: 500, 1,000 y 1,500 mGy | Tabla 4.8-1 |

Usa datos reales de RadLab para alimentar el simulador y la norma para los límites. Las dosis de la norma dependen de modelos específicos de NASA (modelo Q, espectro GCR de mínimo solar 2009), así que los valores de nuestro prototipo serán aproximados.

### Nivel 3: criterios del cuerpo relativos a la línea base

| Parámetro | Criterio | Requisito |
| --- | --- | --- |
| Capacidad aeróbica en misión | ≥ 80% del valor previo a la misión | [V1 4003] |
| VO₂max absoluto | ≥ 32.9 mL/min/kg (EVA en microgravedad); ≥ 36.5 (EVA en superficie) | [V1 4001] [V1 4002] |
| Fuerza muscular en misión | ≥ 80% de la línea base | [V1 4024] |
| Densidad ósea en misión | ≥ 95% de la previa (cadera y columna); ≥ 90% (cuello femoral) | [V1 4027] |
| Energía diaria | 3,035 kcal promedio por tripulante, o fórmula EER con factor de actividad de 1.0 a 1.25; +200 kcal por hora de EVA | [V2 7003] [V2 7004] |
| Vitamina D | 25 µg al día | Tabla 7.1-2 |
| Sueño (valor por defecto configurable) | Periodo de 8.5 h, más 2 h antes y 1.5 h después; mínimo circadiano entre la 1 y las 7 AM | [V1 6001] (justificación, no requisito) |

### Nivel 4: conocimiento cualitativo para el puerto de conocimiento (RAG)

- **Síntomas de CO₂:** dolor de cabeza entre 2.8 y 4.5 mmHg; fatiga, mal sueño y náuseas por encima de 4.5 (TB-004).
- **Síntomas de hipoxia:** cambios mentales a veces imperceptibles para el astronauta, visión reducida, fatiga, náuseas, dolor de cabeza, mareo, hiperventilación (TB-003). Es un argumento a favor de que la alarma venga del sensor ambiental y no del propio astronauta.
- **Hiperoxia:** reduce ventilación y frecuencia cardíaca; el tratamiento es bajar la ppO₂ (TB-003).
- **Enfermedad por descompresión:** tratamiento con recompresión y O₂ al 100% (TB-003).
- **Mareo espacial:** dura unos 3 días en promedio (TB-044).
- **Rol del oficial médico (CMO):** dos por incremento; la decisión médica recae en el cirujano de vuelo en tierra, con el grupo médico internacional en casos agudos. Sirve para definir cuándo la alerta escala a Tierra (TB-044).
- **Mediciones a bordo (checklist del botiquín):** oxímetro de sangre, tensiómetro, termómetro, estetoscopio, otoscopio, tonómetro, tiras de orina.
- **Medidas a activar:** el botiquín da categorías de fármacos por condición (náuseas, sueño, dolor, alergias, mal de altura con acetazolamida, entre otras). Sirve para el catálogo de acciones.

### Lo que no está en los documentos públicos

- Umbrales de ritmo cardíaco, presión arterial y SpO₂. Habrá que usar otra fuente citable (por ejemplo la escala NEWS2) o etiquetarlos como parámetros de demostración.
- Valores críticos de hematología e inmunología, y límites de horas de trabajo y sueño: la norma dice que existen pero no los publica en este texto.
- Límites de CO₂ a 24 h, 7 y 1000 días en la norma: no aparecieron en la parte leída de Vol. 2. El valor de 2.5 mmHg a 7 días viene del Technical Brief de CO₂.
- Tabla 10.3-1 (alertas) de Vol. 2: no apareció en el tramo leído.
- Consumo de oxígeno por tripulante para el presupuesto de misión: no confirmado en esta lectura.

### Propuesta de estructura para el catálogo de reglas

Cada regla como un registro con: parámetro, operador, valor, unidad, ventana de tiempo, severidad, requisito de origen y estado (verificado en norma, derivado de Technical Brief o parámetro de demostración). Así el puerto de conocimiento puede mostrar la fuente de cada alerta y el adaptador de demostración queda marcado.

## 5d. Bosquejo de ideas que podemos implementar

Notas sueltas de lo que hemos ido hablando. Son ideas para armar, no cosas cerradas.

### Modo autónomo local

Todo el sistema vive en un equipo local a bordo, sin depender del enlace con el centro de control. Los datos, las reglas y los PDFs de NASA se quedan dentro. Si la conexión se corta, la tripulación sigue recibiendo alertas y recomendaciones con su fuente. Cuando vuelve el enlace, se sincroniza con Tierra.

Por decidir:

- Qué se sube al centro de control al reconectar y si el astronauta elige qué compartir.
- Si el buscador de documentos solo devuelve pasajes con su cita o también redacta con un modelo de lenguaje.

### Qué vería el centro de control

Todos los datos serían visibles desde el centro de control cuando haya conexión: signos vitales, ambiente de la cabina, radiación, sueño y las alertas que se hayan generado.

### Datos de sueño

Lo que encontramos en fuentes de NASA:

- Los astronautas usan pulseras de actigrafía (Actiwatch Spectrum), que miden movimiento y luz ambiente en la muñeca. Sirven para estimar horas de sueño, no las fases.
- El estudio Standard Measures usa un cuestionario antes y después de dormir sobre calidad del sueño, ánimo, cohesión del equipo y desempeño.
- Cada astronauta tiene un cuarto de tripulación para dormir, con límite de ruido NC-40 según la norma.
- Los astronautas duermen en promedio unas seis horas en el espacio.

Lo que no encontramos: un compartimento de dormir que mida el sueño por sí solo. Esa parte la dejamos como idea para explorar, por ejemplo un módulo de dormir con sensores de ruido, luz, temperatura y movimiento.

Datos que el centro de control podría ver por astronauta: horas de sueño por noche, tendencia de varios días contra su línea base, luz ambiente, respuestas del cuestionario y ruido del cuarto.

### Asistente con modelo de lenguaje local

Usar un modelo local con Ollama en lugar de una API externa como OpenAI, Gemini o Anthropic, para que funcione sin internet.

Flujo pensado, montado sobre n8n:

1. Los sensores y las reglas pasan primero por el backend.
2. Cuando hay un evento, el backend se lo manda al agente en n8n.
3. El agente consulta el RAG con los PDFs de NASA.
4. Con lo que encuentra, resume y devuelve la respuesta con su fuente.

La idea es que Ollama solo use el RAG como herramienta complementaria. Las reglas siguen siendo las que deciden cuándo hay una alerta, y el modelo se encarga de explicarla.

Cuidados a tener en cuenta:

- Que el modelo responda solo con lo recuperado del RAG y diga que no tiene la información si no hay un pasaje que la respalde, para que no invente protocolos médicos.
- Probar un modelo pequeño que corra bien en el equipo de la demo.

### Entrada por voz

Para que la tripulación no tenga que escribir, un astronauta puede hablar y el sistema transcribe lo que dice a texto. Ese texto pasa por Ollama y el RAG.

Flujo pensado: voz, transcripción local (por ejemplo Whisper, que corre sin internet), texto, agente con RAG, respuesta en texto o con una voz local.

Cuidados a tener en cuenta:

- La transcripción puede fallar con términos médicos o con el ruido de la cabina, así que conviene mostrar lo transcrito para confirmarlo antes de actuar.
- En una emergencia, la alerta no debe depender de que el astronauta hable. Debe salir de los sensores.

### Voz: Whisper primero, Alexa como respaldo

La idea es usar Whisper como transcripción principal. Si vemos que nos trabamos con la transcripción, usamos Alexa como respaldo para la demo. Como el proyecto está en arquitectura hexagonal, la voz es un adaptador intercambiable y el núcleo, las reglas y Ollama no cambian.

Dos perfiles de desarrollo (configuraciones que se activan al arrancar el proyecto, no perfiles de usuario):

- **Perfil de presentación:** activa el adaptador de Alexa para la voz, en caso de que Whisper no nos funcione bien. Requiere crear el skill de Alexa y un endpoint público (por ejemplo con un túnel) para que Alexa llegue al backend o a n8n.
- **Perfil para jurado:** activa el adaptador de Whisper local y funciona totalmente sin la conexión con Alexa. Es el que muestra el sistema autónomo, sin internet.

Notas para tener a la mano:

- Los perfiles se cambian con una variable de entorno de perfil. Son tres valores: dev1 arranca con Whisper, dev2 arranca con Alexa y jurado arranca con Whisper. Los perfiles dev son para desarrollo y el perfil jurado es para que el jurado del concurso pueda ejecutar todo de manera correcta. Que dev1 y jurado usen lo mismo es a propósito: separa lo que es de desarrollo de lo que es de entrega y deja ver que hay orden en los perfiles. El nombre exacto de la variable y el valor por defecto están por definir.
- Alexa procesa la voz en la nube, así que no es autónoma. Es un adaptador temporal para la demo, y conviene decirlo así en la presentación.
- Un skill en modo desarrollo corre solo en nuestra cuenta, lo cual alcanza para la demo.
- Tener un plan B con texto escrito por si falla el wifi del evento.
- Estimación de tiempo para Whisper: una o dos horas para tener la primera transcripción conectada al backend, y otra hora o dos de pruebas con ruido de fondo y términos médicos. Es una estimación general, no verificada con nuestro equipo.

### Entrega para el jurado con Docker

El jurado va a revisar el código y también a ejecutar el programa. Para evitar el problema de que en nuestra computadora funciona y en la de ellos no, vamos a crear una imagen de Docker y publicarla en Docker Hub, para que puedan ejecutarla en un contenedor sin instalar nada a mano.

Ideas para tener a la mano:

- Que la imagen arranque por defecto con el perfil jurado, que usa Whisper local y no necesita Alexa.
- Que el perfil se pueda cambiar con la variable de entorno al correr el contenedor, por ejemplo para usar dev1 o dev2 nosotros.
- Incluir en la imagen todo lo que necesita sin internet: el backend, la base de reglas, los PDFs de NASA ya indexados y el modelo de Whisper. Así el jurado no espera descargas ni depende de la red del evento.
- Ollama y su modelo ocupan mucho espacio. Hay que decidir si van dentro de la misma imagen o en un segundo contenedor, por ejemplo con Docker Compose junto con n8n.
- Dejar en el README el comando exacto para descargar y correr la imagen, y el enlace al repositorio con el código.

Por revisar:

- El tamaño final de la imagen, para que descargarla desde Docker Hub no tarde demasiado.
- Si el equipo del jurado tiene tarjeta gráfica. Sin ella, Ollama y Whisper correrán más lento y hay que probar con un modelo pequeño.
- El micrófono dentro del contenedor: acceder al audio del equipo desde Docker puede dar problemas según el sistema operativo, y conviene tener la entrada por texto como alternativa.

### Gases adicionales: nitrógeno, metano y vapor de agua

Idea para ampliar los índices de la cabina con tres gases más. Notas de dónde estamos con cada uno:

- **Nitrógeno:** hoy solo lo tenemos de forma indirecta, como gas diluyente. La norma pide al menos 30% de gas diluyente en la atmósfera ([V2 6002]) y el nitrógeno es el diluyente más común. La idea es medirlo como gas propio y calcular su presión parcial, igual que el oxígeno.
- **Metano:** no aparece en nada de lo que hemos leído. La norma remite a una lista de límites máximos permitidos para contaminantes del aire (SMAC, documento JSC-20584), que todavía no hemos abierto. Hasta revisarla, cualquier umbral de metano sería un dato de demostración y debe rotularse así.
- **Vapor de agua:** ya tenemos la humedad relativa con sus límites (18 °C con 75% hasta 27 °C con 25%, y la zona de desempeño de 20 a 25 °C con 30 a 60%). La idea es mostrarlo también como gas de la mezcla. Un dato útil: la presión del vapor de agua en los pulmones es de 47 mmHg, y es la que se resta al calcular el oxígeno inspirado.

Por decidir:

- Si el nitrógeno y el vapor de agua se leen de sensores propios o se calculan a partir de los otros datos.
- Abrir la lista de contaminantes (SMAC) para ver si trae el metano y con qué límites.

## 6. Decisiones

| Decisión | Fecha | Motivo |
| --- | --- | --- |
|  |  |  |

## 7. Pendientes

- [ ]  Leer la ficha oficial del reto y sus recursos
- [ ]  Definir alcance del MVP según el tiempo restante
- [ ]  Repartir roles del equipo
- [x]  Elegir qué PDFs públicos de NASA usar y comprobar que se pueden descargar (ver sección 5b; quedan por abrir varios documentos)
- [ ]  Encontrar fuente para umbrales de signos vitales del cuerpo (ver 5c; no están en Vol. 1, Vol. 2 ni los Technical Briefs leídos)
- [ ]  Decidir si el catálogo de reglas se escribe en JSON y quién lo mantiene
- [ ]  Probar un modelo pequeño con Ollama en el equipo de la demo
- [ ]  Probar Whisper local con ruido de fondo
- [x]  Definir los perfiles de desarrollo y cómo se cambia entre ellos: se decidió con una variable de entorno con tres valores (dev1 con Whisper, dev2 con Alexa, jurado con Whisper)
- [ ]  Elegir el nombre de la variable de entorno y su valor por defecto
- [ ]  Abrir la lista de contaminantes del aire (SMAC, JSC-20584) y buscar metano
- [ ]  Decidir si nitrógeno y vapor de agua se miden o se calculan
- [ ]  Crear el Dockerfile y publicar la imagen en Docker Hub
- [ ]  Decidir si Ollama va en la misma imagen o en un contenedor aparte con Docker Compose
- [ ]  Probar el contenedor en otra computadora, sin internet, antes de entregar
- [ ]  Escribir en el README el comando para descargar y ejecutar la imagen
- [ ]  Crear el skill de Alexa y el túnel solo si Whisper se traba
- [ ]  Armar el flujo en n8n: backend, agente, RAG y respuesta
- [ ]  Decidir qué datos de sueño vamos a simular
- [ ]  Confirmar si "RAC" era RAG y decidir si el sistema usa un modelo de lenguaje o solo búsqueda de pasajes

## 8. Fuentes

- [Resumen del reto (Sonoma State)](https://edeon.sonoma.edu/nasaspaceapps-26/)
- [NASA: Space Apps 2026](https://science.nasa.gov/universe/nasa-welcomes-all-ages-experience-levels-for-space-apps-challenge/)
- [AstroHealth](https://github.com/Ridwanulkarim/nasa-challenge-Create-Health-Monitoring-Software-for-Astronauts-on-Space-Missions)
- [AURORA](https://github.com/fabriciojunio/aurora-astronaut-health)
- [Crew Health Monitor](https://github.com/AdityaK0804/Crew-Health-Monitor)