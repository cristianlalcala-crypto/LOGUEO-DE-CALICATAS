# -*- coding: utf-8 -*-
"""Almacenamiento local en SQLite. Cada registro queda guardado en el
telefono aunque no haya senal; 'sincronizado' marca si ya se exporto/envio."""

import sqlite3
import uuid
import datetime

CAMPOS = [
    "proyecto", "sondeo", "coord_este", "coord_norte",
    "prof_desde", "prof_hasta", "nivel_roca", "nivel_agua",
    "simbolo_uscs", "nombre_grupo", "color", "humedad",
    "consistencia_compacidad", "plasticidad", "resistencia_seca",
    "dilatancia", "tenacidad", "estructura", "forma_particulas",
    "tamano_max_particula", "reaccion_hcl", "olor",
    "formacion", "comentarios",
]

DDL = """
CREATE TABLE IF NOT EXISTS registros (
    id TEXT PRIMARY KEY,
    tecnico TEXT,
    fecha_hora TEXT,
    """ + ",\n    ".join(f"{c} TEXT" for c in CAMPOS) + """,
    descripcion_generada TEXT,
    sincronizado INTEGER DEFAULT 0
);
"""


def conectar(path="bitacora_local.db"):
    conn = sqlite3.connect(path)
    conn.execute(DDL)
    conn.commit()
    return conn


def guardar_registro(conn, record: dict, tecnico: str, descripcion: str) -> str:
    """Inserta un registro nuevo. Devuelve el id (uuid) generado.
    'id' unico es lo que permite luego consolidar los excels de varios
    tecnicos sin duplicar filas."""
    rid = str(uuid.uuid4())
    fecha_hora = datetime.datetime.now().isoformat(timespec="seconds")
    valores = [rid, tecnico, fecha_hora] + [record.get(c, "") for c in CAMPOS] + [descripcion, 0]
    placeholders = ",".join("?" * len(valores))
    columnas = "id, tecnico, fecha_hora, " + ", ".join(CAMPOS) + ", descripcion_generada, sincronizado"
    conn.execute(f"INSERT INTO registros ({columnas}) VALUES ({placeholders})", valores)
    conn.commit()
    return rid


def listar_registros(conn, solo_no_sincronizados: bool = False):
    columnas = "id, tecnico, fecha_hora, " + ", ".join(CAMPOS) + ", descripcion_generada, sincronizado"
    query = f"SELECT {columnas} FROM registros"
    if solo_no_sincronizados:
        query += " WHERE sincronizado = 0"
    query += " ORDER BY fecha_hora DESC"
    cur = conn.execute(query)
    nombres = [d[0] for d in cur.description]
    return [dict(zip(nombres, fila)) for fila in cur.fetchall()]


def marcar_sincronizados(conn, ids: list):
    conn.executemany("UPDATE registros SET sincronizado = 1 WHERE id = ?", [(i,) for i in ids])
    conn.commit()


def eliminar_registro(conn, rid: str):
    conn.execute("DELETE FROM registros WHERE id = ?", (rid,))
    conn.commit()
