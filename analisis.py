import pandas as pd
import json


# ============================================================
# 1. CARGA Y LIMPIEZA DEL ARCHIVO
# ============================================================

def cargar_datos(ruta):
    """
    Lee el archivo de prueba delimitado por '|'.

    El archivo contiene un delimitador al inicio y al final
    de cada fila, por lo que se eliminan esos elementos vacíos.
    También se validan las filas para conservar únicamente
    aquellas que tienen la misma cantidad de campos que el encabezado.
    """
    filas = []

    with open(ruta, "r", encoding="utf-8", errors="replace") as archivo:

        # Leer encabezado y eliminar los delimitadores vacíos de los extremos
        encabezado = archivo.readline().rstrip("\r\n").split("|")[1:-1]

        # Saltar la fila separadora del archivo
        archivo.readline()

        # Leer los registros
        for linea in archivo:
            valores = linea.rstrip("\r\n").split("|")[1:-1]

            if len(valores) == len(encabezado):
                filas.append(valores)

    df = pd.DataFrame(filas, columns=encabezado)

    return df


# Ruta del archivo de entrada
ruta = "datos_ejemplo/prueba_ejemplo.txt"

# Cargar los datos
df = cargar_datos(ruta)

# Eliminar espacios residuales de los nombres de las columnas
df.columns = df.columns.str.strip()

# Eliminar espacios residuales de las columnas de texto
columnas_texto = df.select_dtypes(include="object").columns
df[columnas_texto] = df[columnas_texto].apply(
    lambda columna: columna.str.strip()
)


# ============================================================
# 2. PREPARACIÓN DE FECHAS
# ============================================================

# Convertir created_at a formato datetime para facilitar
# posteriormente el análisis temporal en Python y SQL.
df["created_at"] = pd.to_datetime(
    df["created_at"],
    errors="coerce"
)


# ============================================================
# 3. PARSEO DE INFORMACIÓN JSON
# ============================================================

def parse_json(texto):
    """
    Convierte una cadena que contiene información JSON
    en un diccionario de Python.

    Algunos campos requieren una segunda decodificación
    porque el JSON está almacenado dentro de una cadena JSON.
    """
    if pd.isna(texto) or not str(texto).strip():
        return {}

    try:
        obj = json.loads(str(texto))

        # Algunos registros contienen JSON anidado como string
        if isinstance(obj, str):
            obj = json.loads(obj)

        return obj if isinstance(obj, dict) else {}

    except (json.JSONDecodeError, TypeError):
        return {}


# ============================================================
# 4. EXTRACCIÓN DE ERRORES Y PLANTILLAS
# ============================================================

# Extraer el error reportado por el sistema desde content_attributes
df["external_error"] = df["content_attributes"].apply(
    lambda x: parse_json(x).get("external_error")
)

# Extraer el nombre de la plantilla desde additional_attributes
df["template_name"] = df["additional_attributes"].apply(
    lambda x: parse_json(x)
    .get("template_params", {})
    .get("name")
)

# Tabla auxiliar para analizar la relación entre plantillas y errores
tabla_errores = pd.crosstab(
    df["template_name"],
    df["external_error"]
)


# ============================================================
# 5. CLASIFICACIÓN BÁSICA DE MENSAJES INCOMING
# ============================================================

# Trabajar únicamente con mensajes enviados por los clientes
mensajes_incoming = df[
    df["message_type"] == "incoming"
].copy()


def clasificar_mensaje(mensaje):

    mensaje = str(mensaje).lower().strip()

    palabras_queja = [
        "inconforme",
        "cobraron",
        "cobrando",
        "no llegó",
        "no ha llegado",
        "qué desastre",
        "demorado",
        "demora",
        "no me ha llegado",
        "rechazado"
    ]

    palabras_soporte = [
        "ayuda",
        "no funciona",
        "no prende",
        "no aparece",
        "no me sale",
        "cómo procedo",
        "revisar",
        "verificar",
        "problema",
        "no me han sumado",
        "no me sumaron",
        "puntos",
        "código",
        "no conozco"
    ]

    palabras_pedido = [
        "pedido",
        "pedidos",
        "hacer pedido",
        "pasar pedido",
        "realizar pedido",
        "pedido mínimo",
        "ingresarlo",
        "ingreso",
        "catalogos",
        "catálogos",
        "en pdf"
    ]

    # Prioridad 1: Queja
    for palabra in palabras_queja:
        if palabra in mensaje:
            return "Queja"

    # Prioridad 2: Soporte
    for palabra in palabras_soporte:
        if palabra in mensaje:
            return "Soporte"

    # Prioridad 3: Pedido
    for palabra in palabras_pedido:
        if palabra in mensaje:
            return "Pedido"

    # Mensajes que no coinciden con ninguna categoría
    return "Otro"


# Aplicar la clasificación a los mensajes incoming
mensajes_incoming["categoria"] = mensajes_incoming[
    "content"
].apply(clasificar_mensaje)

df.loc[mensajes_incoming.index, "categoria"] = mensajes_incoming["categoria"]
# ============================================================
# 6. EXPORTACIÓN DEL DATASET PROCESADO
# ============================================================

# Exportar los datos preparados para su uso posterior
# en SQL y herramientas de visualización.
df.to_csv(
    "datos_limpios.csv",
    index=False,
    encoding="utf-8-sig"
)

# 2A. GUARDAR DATOS EN SQLITE y Funnel de Entrega
import sqlite3

conexion = sqlite3.connect("prueba.db")

df.to_sql(
    "messages",
    conexion,
    if_exists="replace",
    index=False
)


# ============================================================
# 9. VALIDACIÓN DE LA CARGA
# ============================================================

consulta = """
SELECT COUNT(*) AS total_mensajes
FROM messages;
"""

resultado = pd.read_sql_query(
    consulta,
    conexion
)

print("\nTotal de mensajes cargados:")
print(resultado)


# ============================================================
# 10. FUNNEL DE ENTREGA
# ============================================================

consulta = """
SELECT
    status,
    COUNT(*) AS cantidad,
    ROUND(
        COUNT(*) * 100.0 /
        SUM(COUNT(*)) OVER (),
        2
    ) AS porcentaje
FROM messages
WHERE message_type = 'outgoing'
GROUP BY status
ORDER BY cantidad DESC;
"""

resultado = pd.read_sql_query(
    consulta,
    conexion
)

print("\nFunnel de entrega:")
print(resultado)


# ============================================================
# 11. SLA DE RESPUESTA
# ============================================================

consulta = """
WITH incoming AS (
    SELECT
        id AS incoming_id,
        conversation_id,
        created_at AS incoming_at
    FROM messages
    WHERE message_type = 'incoming'
),

acciones AS (
    SELECT
        id AS action_id,
        conversation_id,
        message_type,
        created_at AS action_at
    FROM messages
    WHERE message_type IN ('activity', 'outgoing')
),

candidatos AS (
    SELECT
        i.incoming_id,
        i.conversation_id,
        i.incoming_at,
        a.action_id,
        a.message_type,
        a.action_at,

        ROW_NUMBER() OVER (
            PARTITION BY i.incoming_id
            ORDER BY a.action_at, a.action_id
        ) AS numero_accion

    FROM incoming i

    JOIN acciones a
        ON a.conversation_id = i.conversation_id
        AND a.action_at > i.incoming_at
),

sla AS (
    SELECT
        (
            julianday(action_at) -
            julianday(incoming_at)
        ) * 24 * 60 AS minutos_respuesta

    FROM candidatos

    WHERE numero_accion = 1
)

SELECT
    COUNT(*) AS mensajes_con_accion,

    ROUND(
        AVG(minutos_respuesta),
        2
    ) AS promedio_sla_minutos,

    ROUND(
        MIN(minutos_respuesta),
        2
    ) AS minimo_minutos,

    ROUND(
        MAX(minutos_respuesta),
        2
    ) AS maximo_minutos

FROM sla;
"""

resultado = pd.read_sql_query(
    consulta,
    conexion
)

print("\nSLA de respuesta:")
print(resultado)


# ============================================================
# 12. VOLUMEN DE MENSAJES INCOMING POR HORA
# ============================================================

consulta = """
SELECT
    strftime('%H', created_at) AS hora,
    COUNT(*) AS mensajes_entrantes
FROM messages
WHERE message_type = 'incoming'
GROUP BY hora
ORDER BY hora;
"""

resultado = pd.read_sql_query(
    consulta,
    conexion
)

print("\nMensajes incoming por hora:")
print(resultado)


# ============================================================
# 13. ERRORES POR PLANTILLA
# ============================================================

consulta = """
SELECT
    COALESCE(template_name, 'Sin plantilla') AS plantilla,
    COALESCE(external_error, 'Sin error') AS error,
    COUNT(*) AS cantidad
FROM messages
WHERE message_type = 'outgoing'
  AND external_error IS NOT NULL
GROUP BY template_name, external_error
ORDER BY cantidad DESC;
"""

resultado = pd.read_sql_query(
    consulta,
    conexion
)

print("\nErrores por plantilla:")
print(resultado)


# ============================================================
# 14. CERRAR CONEXIÓN
# ============================================================

conexion.close()

print("\nProceso finalizado correctamente.")