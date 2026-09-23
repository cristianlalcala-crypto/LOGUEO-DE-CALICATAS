# -*- coding: utf-8 -*-
"""
Bitacora Geotecnica - app Android (Kivy)
Captura de descripcion visual de suelos segun ASTM D2488 / USCS.
Funciona sin conexion: todo se guarda en SQLite local en el telefono.
"""

import os
import json

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.metrics import dp

import db
import descripcion
import export_xlsx

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VOCAB_PATH = os.path.join(BASE_DIR, "vocab.json")
LOGO_PATH = os.path.join(BASE_DIR, "assets", "jmf_logo.jpg")


def cargar_vocab():
    with open(VOCAB_PATH, encoding="utf-8") as f:
        return json.load(f)


class Encabezado(BoxLayout):
    """Barra superior con el logo de JMF Ingenieria & Construccion."""
    def __init__(self, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(64),
                          padding=(dp(10), dp(6)), spacing=dp(10), **kwargs)
        if os.path.exists(LOGO_PATH):
            self.add_widget(Image(source=LOGO_PATH, size_hint_x=None, width=dp(120)))
        titulo = Label(text="Bitacora Geotecnica - ASTM D2488", bold=True,
                        color=(0.12, 0.29, 0.47, 1), halign="left", valign="middle")
        titulo.bind(size=lambda *a: setattr(titulo, "text_size", titulo.size))
        self.add_widget(titulo)


class CampoTexto(BoxLayout):
    """Etiqueta + TextInput de una sola linea."""
    def __init__(self, etiqueta, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, height=dp(64), **kwargs)
        self.add_widget(Label(text=etiqueta, size_hint_y=None, height=dp(20),
                               halign="left", valign="bottom", color=(0.2, 0.2, 0.2, 1)))
        self.input = TextInput(multiline=False, size_hint_y=None, height=dp(40))
        self.add_widget(self.input)

    @property
    def value(self):
        return self.input.text.strip()


class CampoLista(BoxLayout):
    """Etiqueta + Spinner (equivalente al 'dropdown' del Excel)."""
    def __init__(self, etiqueta, opciones, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, height=dp(64), **kwargs)
        self.add_widget(Label(text=etiqueta, size_hint_y=None, height=dp(20),
                               halign="left", valign="bottom", color=(0.2, 0.2, 0.2, 1)))
        self.spinner = Spinner(text="", values=[""] + opciones, size_hint_y=None, height=dp(40))
        self.add_widget(self.spinner)

    @property
    def value(self):
        return self.spinner.text.strip()


class FormularioBitacora(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.add_widget(Encabezado())
        self.vocab = cargar_vocab()
        # user_data_dir es la carpeta privada de la app en el telefono:
        # persiste entre sesiones y no necesita permisos especiales.
        carpeta_datos = App.get_running_app().user_data_dir
        db_path = os.path.join(carpeta_datos, "bitacora_local.db")
        self.conn = db.conectar(db_path)
        self.campos = {}

        scroll = ScrollView()
        self.form_layout = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6),
                                      padding=dp(12))
        self.form_layout.bind(minimum_height=self.form_layout.setter("height"))
        scroll.add_widget(self.form_layout)
        self.add_widget(scroll)

        self._agregar_texto("proyecto", "Nombre del proyecto")
        self._agregar_texto("sondeo", "Sondeo / Pozo")
        self._agregar_texto("coord_este", "Coordenada Este (UTM)")
        self._agregar_texto("coord_norte", "Coordenada Norte (UTM)")
        self._agregar_texto("prof_desde", "Profundidad desde (m)")
        self._agregar_texto("prof_hasta", "Profundidad hasta (m)")
        self._agregar_texto("nivel_roca", "Nivel de roca (m)")
        self._agregar_texto("nivel_agua", "Nivel de agua (m)")
        self._agregar_lista("simbolo_uscs", "Simbolo USCS", "simbolo_uscs")
        self._agregar_texto("nombre_grupo", "Nombre de grupo (ASTM D2487)")
        self._agregar_lista("color", "Color", "color")
        self._agregar_lista("humedad", "Humedad", "humedad")
        self._agregar_lista("consistencia_compacidad", "Consistencia / Compacidad", "consistencia_compacidad")
        self._agregar_lista("plasticidad", "Plasticidad", "plasticidad")
        self._agregar_lista("resistencia_seca", "Resistencia en seco", "resistencia_seca")
        self._agregar_lista("dilatancia", "Dilatancia", "dilatancia")
        self._agregar_lista("tenacidad", "Tenacidad", "tenacidad")
        self._agregar_lista("estructura", "Estructura", "estructura")
        self._agregar_lista("forma_particulas", "Forma de particulas", "forma_particulas")
        self._agregar_lista("tamano_max_particula", "Tamano max. de particula", "tamano_max_particula")
        self._agregar_lista("reaccion_hcl", "Reaccion con HCl", "reaccion_hcl")
        self._agregar_lista("olor", "Olor", "olor")
        self._agregar_texto("formacion", "Formacion geologica / Nombre local")
        self._agregar_texto("comentarios", "Comentarios adicionales")

        # Vista previa de la descripcion generada (se actualiza al guardar)
        self.preview = Label(text="", size_hint_y=None, height=dp(90),
                              halign="left", valign="top", color=(0.1, 0.35, 0.1, 1))
        self.preview.bind(size=lambda *a: setattr(self.preview, "text_size", self.preview.size))
        self.form_layout.add_widget(self.preview)

        botones = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(8), padding=dp(8))
        btn_guardar = Button(text="Guardar registro")
        btn_guardar.bind(on_release=self.guardar)
        btn_exportar = Button(text="Exportar Excel")
        btn_exportar.bind(on_release=self.exportar)
        botones.add_widget(btn_guardar)
        botones.add_widget(btn_exportar)
        self.add_widget(botones)

        self.contador = Label(text=self._texto_contador(), size_hint_y=None, height=dp(28))
        self.add_widget(self.contador)

    def _agregar_texto(self, clave, etiqueta):
        campo = CampoTexto(etiqueta)
        self.campos[clave] = campo
        self.form_layout.add_widget(campo)

    def _agregar_lista(self, clave, etiqueta, nombre_vocab):
        campo = CampoLista(etiqueta, self.vocab[nombre_vocab])
        self.campos[clave] = campo
        self.form_layout.add_widget(campo)

    def _texto_contador(self):
        total = len(db.listar_registros(self.conn))
        pendientes = len(db.listar_registros(self.conn, solo_no_sincronizados=True))
        return f"Registros guardados en este telefono: {total}  (sin exportar: {pendientes})"

    def _leer_formulario(self):
        return {clave: campo.value for clave, campo in self.campos.items()}

    def _limpiar_formulario(self):
        for campo in self.campos.values():
            if isinstance(campo, CampoTexto):
                campo.input.text = ""
            else:
                campo.spinner.text = ""

    def _mostrar_aviso(self, mensaje):
        Popup(title="Bitacora", content=Label(text=mensaje),
              size_hint=(0.8, 0.3)).open()

    def guardar(self, *_):
        record = self._leer_formulario()
        if not record.get("proyecto") or not record.get("sondeo"):
            self._mostrar_aviso("Falta Proyecto o Sondeo/Pozo.")
            return
        desc = descripcion.generar_descripcion(record)
        # tecnico: por ahora fijo/simple; se puede cambiar por login si se requiere
        tecnico = os.environ.get("USER", "Tecnico de campo")
        db.guardar_registro(self.conn, record, tecnico=tecnico, descripcion=desc)
        self.preview.text = "Descripcion generada:\n" + desc
        self.contador.text = self._texto_contador()
        self._limpiar_formulario()
        self._mostrar_aviso("Registro guardado en el telefono.")

    def exportar(self, *_):
        registros = db.listar_registros(self.conn)
        if not registros:
            self._mostrar_aviso("No hay registros guardados todavia.")
            return
        carpeta = App.get_running_app().user_data_dir
        ruta = os.path.join(carpeta, "bitacora_exportada.xlsx")
        export_xlsx.exportar_a_xlsx(registros, ruta)
        ids = [r["id"] for r in registros]
        db.marcar_sincronizados(self.conn, ids)
        self.contador.text = self._texto_contador()
        self._mostrar_aviso(f"Excel exportado en:\n{ruta}\n\nCompartelo por WhatsApp/correo/Drive\ncuando tengas señal.")


class BitacoraApp(App):
    def build(self):
        self.title = "Bitacora Geotecnica"
        return FormularioBitacora()


if __name__ == "__main__":
    BitacoraApp().run()
