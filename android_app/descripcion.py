# -*- coding: utf-8 -*-
"""
Genera la descripcion visual estandar a partir de los campos capturados,
en el mismo orden y con el mismo formato que la formula del Excel
"Bitacora_Geotecnica_ASTM_D2488.xlsx", para que ambos sistemas sean
consistentes sin importar donde se capturo el dato.
"""

# Replica EXACTA, campo por campo, de la formula del Excel:
# IF(campo="","","prefijo"&campo&"sufijo")  concatenados en este orden.
# Si cambias el orden o el texto aqui, cambia tambien la formula de la
# hoja "Bitacora" del Excel (build_bitacora.py) para que no se desalineen.
_PASOS = [
    ("nombre_grupo", "", " "),
    ("simbolo_uscs", "(", ") "),
    ("color", "color ", ", "),
    ("humedad", "humedad ", ", "),
    ("consistencia_compacidad", "consistencia/compacidad ", ", "),
    ("plasticidad", "plasticidad ", ", "),
    ("resistencia_seca", "resistencia en seco ", ", "),
    ("dilatancia", "dilatancia ", ", "),
    ("tenacidad", "tenacidad ", ", "),
    ("estructura", "estructura ", ", "),
    ("forma_particulas", "particulas ", ", "),
    ("tamano_max_particula", "tamano max. ", ", "),
    ("reaccion_hcl", "reaccion HCl: ", ", "),
    ("olor", "olor: ", ", "),
    ("formacion", "Formacion/nombre local: ", ". "),
    ("comentarios", "Obs: ", "."),
]


def generar_descripcion(record: dict) -> str:
    """record: dict con las claves de los campos ASTM D2488 (ver db.CAMPOS).
    Devuelve el mismo texto, caracter por caracter, que produce la formula
    de la columna 'DESCRIPCION ESTANDAR' del Excel."""
    texto = ""
    for campo, prefijo, sufijo in _PASOS:
        valor = (record.get(campo) or "").strip()
        if valor:
            texto += f"{prefijo}{valor}{sufijo}"
    return texto.strip()
