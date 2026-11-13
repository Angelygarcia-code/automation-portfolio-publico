"""
Genera un archivo de mensajería SINTÉTICO con la misma estructura que el archivo
real usado para desarrollar el análisis (texto delimitado por '|').
Todos los datos son inventados: no corresponden a personas ni empresas reales.
"""
import json
import random
from datetime import datetime, timedelta

random.seed(42)

COLUMNAS = [
    "id", "content", "account_id", "inbox_id", "conversation_id", "message_type",
    "created_at", "updated_at", "private", "status", "source_id", "content_type",
    "content_attributes", "sender_type", "sender_id", "additional_attributes",
    "processed_message_content", "sentiment", "contact_id", "sistema_lead_id",
    "conversation_display_id", "id_sistema", "id_db_externa", "id_leads_db_externa",
]

INCOMING = {
    "queja": ["Estoy inconforme, mi pedido no llegó", "Me siguen cobrando y no he recibido nada",
              "Qué desastre, el envío viene muy demorado"],
    "soporte": ["Necesito ayuda, la app no funciona", "No me sumaron los puntos de mi compra",
                "Tengo un problema con el código de descuento"],
    "pedido": ["Quiero hacer un pedido", "Cuál es el pedido mínimo?", "Me pueden enviar los catálogos en PDF?"],
    "otro": ["Hola, buenas tardes", "Gracias!", "Ok, listo"],
}
PLANTILLAS = ["bienvenida_cliente", "recordatorio_pedido", "promo_semana"]
ERRORES = ["131026: Message undeliverable", "131049: Message not delivered to maintain healthy ecosystem engagement"]
INICIO = datetime(2025, 3, 3, 0, 0, 0)

def hora_aleatoria(dia):
    pesos = [1,1,1,1,1,2,3,6,9,10,9,6,5,6,8,9,8,6,4,3,2,2,1,1]
    h = random.choices(range(24), weights=pesos)[0]
    return INICIO + timedelta(days=dia, hours=h, minutes=random.randint(0, 59), seconds=random.randint(0, 59))

def fila(vals):
    return "|" + "|".join(str(v) for v in vals) + "|"

filas, msg_id = [], 1000
for conv in range(1, 141):
    dia = random.randint(0, 6)
    t = hora_aleatoria(dia)
    contact = 500 + conv
    def base(mtype, status, content, ts, content_attr="{}", add_attr="{}"):
        global msg_id
        msg_id += 1
        return [msg_id, content, 1, 1, conv, mtype, ts.strftime("%Y-%m-%d %H:%M:%S"),
                ts.strftime("%Y-%m-%d %H:%M:%S"), "false", status, f"src_{msg_id}", "text",
                content_attr, "Contact" if mtype == "incoming" else "User", contact, add_attr,
                content, "neutral", contact, 9000 + conv, conv, 7000 + conv, "", ""]
    # mensaje saliente inicial con plantilla (algunos fallan)
    estado = random.choices(["sent", "delivered", "read", "failed"], weights=[30, 8, 20, 42])[0]
    plantilla = random.choice(PLANTILLAS)
    attr = json.dumps({"template_params": {"name": plantilla, "language": "es"}})
    c_attr = "{}"
    if estado == "failed":
        c_attr = json.dumps({"external_error": random.choice(ERRORES)})
        if random.random() < 0.4:               # JSON anidado como texto (caso que el script maneja)
            c_attr = json.dumps(c_attr)
    filas.append(base("outgoing", estado, f"[plantilla {plantilla}]", t, c_attr, attr))
    # respuesta del cliente (la mayoría de los que no fallaron)
    if estado != "failed" and random.random() < 0.75:
        for _ in range(random.randint(1, 3)):
            t += timedelta(minutes=random.randint(1, 90))
            cat = random.choices(list(INCOMING), weights=[10, 20, 25, 45])[0]
            filas.append(base("incoming", "sent", random.choice(INCOMING[cat]), t))
            t += timedelta(minutes=random.choice([1, 2, 3, 5, 8, 15, 45, 120]))
            if random.random() < 0.85:
                filas.append(base("activity", "sent", "Conversación asignada a Asesor Demo", t))
            if random.random() < 0.8:
                t += timedelta(minutes=random.randint(1, 20))
                filas.append(base("outgoing", random.choice(["sent", "read", "delivered"]), "Respuesta del asesor", t))

with open("datos_ejemplo/prueba_ejemplo.txt", "w", encoding="utf-8") as f:
    f.write(fila(COLUMNAS) + "\n")
    f.write("|" + "|".join("---" for _ in COLUMNAS) + "|\n")
    for r in filas:
        f.write(fila(r) + "\n")
print("Filas generadas:", len(filas))
