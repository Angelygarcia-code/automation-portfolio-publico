# Análisis de datos de mensajería con Python y SQL

Proyecto independiente de procesamiento y análisis de datos: convierte una exportación de mensajería de atención al cliente en un conjunto de datos limpio y calcula métricas operativas con SQL.

## Problema
Las exportaciones de mensajería vienen como texto plano con delimitadores y campos JSON anidados. Revisarlas a mano es lento, propenso a errores y no responde preguntas operativas: ¿cuántos mensajes fallan y por qué?, ¿cuánto tarda el equipo en responder?, ¿a qué horas llega la demanda?

## Solución
Un pipeline en Python que carga y limpia el archivo, extrae información de campos JSON anidados, clasifica los mensajes entrantes, guarda todo en SQLite y calcula las métricas con consultas SQL.

## Qué hace, paso a paso
1. **Carga y validación:** lee el archivo delimitado por `|`, elimina los delimitadores de los extremos y descarta filas con un número distinto de campos que el encabezado.
2. **Limpieza:** quita espacios residuales y convierte `created_at` a fecha.
3. **Parseo de JSON anidado:** extrae el error reportado (`external_error`) y el nombre de la plantilla (`template_name`), incluso cuando el JSON viene codificado dos veces.
4. **Clasificación básica:** etiqueta los mensajes entrantes como Queja, Soporte, Pedido u Otro con reglas por palabras clave.
5. **Carga en SQLite y métricas con SQL:**
   - Funnel de entrega (porcentaje de mensajes salientes por estado).
   - SLA de respuesta (tiempo hasta la siguiente acción dentro de la conversación; CTEs y `ROW_NUMBER()`).
   - Curva horaria de mensajes entrantes.
   - Errores por plantilla.

## Herramientas
Python · pandas · json · sqlite3 · SQL (CTE, funciones ventana)

## Sobre los datos
Este repositorio usa **datos sintéticos** con la misma estructura que el archivo original (`datos_ejemplo/`). Los datos con los que desarrollé el análisis contienen conversaciones de terceros y no se publican.

## Cómo ejecutarlo
```bash
pip install -r requirements.txt
python analisis.py
```
Genera `datos_limpios.csv` y `prueba.db` (ignorados por git) e imprime las métricas. Para regenerar los datos de ejemplo: `python datos_ejemplo/generar_datos_ejemplo.py`.

## Ejemplo de salida (con datos sintéticos, no son resultados reales)
| Estado | Cantidad | % |
|---|---|---|
| sent | 75 | 33.33 |
| failed | 63 | 28.00 |
| read | 56 | 24.89 |
| delivered | 31 | 13.78 |

SLA de respuesta: 109 mensajes con acción, promedio de 27.42 minutos (mínimo 1, máximo 136).

## Limitaciones y mejoras posibles
- La clasificación por palabras clave es básica; podría reemplazarse por un modelo de IA.
- El SLA cuenta como "acción" cualquier actividad o mensaje saliente posterior, incluidas acciones automáticas, no solo respuestas humanas.
- La curva horaria usa la hora tal como viene en los datos; habría que confirmar la zona horaria.
