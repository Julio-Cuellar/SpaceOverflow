# Ollama local (modelo del asistente)

Ollama en Docker para el agente de n8n. El modelo vive en un volumen. Todo corre en local, sin internet una vez descargado.

## Preparación (una vez, con internet)

```bash
docker pull ollama/ollama:latest                    # 3,4 GB comprimidos; unos 8,5 GB en disco
docker volume create spaceapp-ollama-models
docker run -d --name spaceapp-ollama -v spaceapp-ollama-models:/root/.ollama \
  -p 127.0.0.1:11434:11434 ollama/ollama:latest
docker exec spaceapp-ollama ollama pull llama3.2:3b   # 2,0 GB
docker cp docker/ollama/Modelfile spaceapp-ollama:/tmp/Modelfile
docker exec spaceapp-ollama ollama create spaceapp-asistente -f /tmp/Modelfile   # sin descargar nada
```

n8n (en otro contenedor) lo alcanza por `http://host.docker.internal:11434`. El modelo que usa el asistente es `spaceapp-asistente`.

## Mediciones en esta máquina (16 hilos lógicos, Docker Desktop con 4 GB, otros contenedores en marcha)

| Prueba | Resultado |
|---|---|
| Primera respuesta con el modelo sin cargar | 190 s (carga 9,8 s; el resto, generar 450 tokens) |
| Generación con los hilos por defecto (16) | **2,6 a 2,7 tok/s** |
| Generación con 4 hilos | **5,8 a 6,5 tok/s** (con 2: 5,2; con 6: 5,6; con 8: 4,5) |
| `spaceapp-asistente` (4 hilos, 150 tokens máx.) | 5,7 tok/s; 109 tokens en 28 s |
| Memoria del contenedor con el modelo cargado | 2,5 GB de los 4 GB que da Docker Desktop |
| Llamada a herramientas (`/api/chat` con `tools`) | funciona: llama a `search_passages` con una consulta razonable, también en una pregunta fuera de alcance |

**Qué significa:** con 16 hilos el modelo compite con los demás contenedores y va más lento que con 4. Una respuesta de 150 tokens tarda unos 25 a 30 s; una de 450, más de un minuto. Por eso el asistente no puede prometer los 8 s del plan: la plantilla con los pasajes sale al instante y la redacción del modelo llega después.

**Calidad observada (una muestra, no una evaluación):** con un pasaje sobre CO₂ y dolor de cabeza en el prompt, el modelo sin acotar contestó largo y genérico («no puedo proporcionar una respuesta médica específica…») en vez de apoyarse en el pasaje. Hace falta limitar la longitud y fijar las instrucciones en n8n, y evaluarlo con las preguntas de `data/knowledge/eval_questions*.json` (fase 6).

## Modelo más pequeño: qwen2.5:1.5b (probado y descartado como agente)

Descargado con permiso del usuario (0,99 GB). Variante `spaceapp-asistente-rapido` en `docker/ollama/Modelfile.qwen1.5b`.

| | llama3.2:3b | qwen2.5:1.5b |
|---|---|---|
| Velocidad (4 hilos) | 6,9 tok/s | **14 a 16 tok/s** (el doble) |
| ¿Llama a la herramienta de búsqueda? | sí | **no, en 0 de 20 preguntas** |
| Evaluación principal por n8n | 9 de 16 con redacción del modelo, 64 s de media | 9 de 16 **pero 16 de 16 por la plantilla de respaldo**, 4,3 s de media |

El modelo pequeño ignora la orden de usar `search_passages` y contesta de memoria («La capital de Francia es París»). El backend lo detecta (no hay pasajes recuperados), descarta ese texto y responde con la plantilla: **la seguridad funcionó, pero el modelo no sirve de agente**. Los 4,3 s de media son los de la plantilla, no los de una redacción. El flujo por defecto sigue con llama3.2:3b.

## Límites

- Mediciones con carga variable (promedio de carga de 7 a 12 durante las pruebas): en otra máquina o sin los otros contenedores serán distintas.
- Sin GPU. AVX2 sí, AVX-512 no.
- La imagen pesa mucho; para la entrega sin internet (F9) imagen y volumen se preparan antes con conexión.
