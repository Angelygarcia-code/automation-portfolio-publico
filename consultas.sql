-- ============================================================
-- 1. FUNNEL DE ENTREGA
-- Porcentaje de mensajes outgoing por estado
-- ============================================================

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


-- ============================================================
-- 2. SLA DE RESPUESTA
-- Tiempo promedio entre mensaje incoming y siguiente
-- acción del asesor dentro de la misma conversación
-- ============================================================

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
    ROUND(AVG(minutos_respuesta), 2) AS promedio_sla_minutos,
    ROUND(MIN(minutos_respuesta), 2) AS minimo_minutos,
    ROUND(MAX(minutos_respuesta), 2) AS maximo_minutos
FROM sla;


-- ============================================================
-- 3. CURVA HORARIA
-- Cantidad de mensajes incoming por hora
-- ============================================================

SELECT
    strftime('%H', created_at) AS hora,
    COUNT(*) AS mensajes_entrantes
FROM messages
WHERE message_type = 'incoming'
GROUP BY hora
ORDER BY hora;