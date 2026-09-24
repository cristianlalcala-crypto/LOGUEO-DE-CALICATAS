# -*- coding: utf-8 -*-
"""
Bitacora Geotecnica - app Android (Kivy)  |  JMF Ingenieria & Construccion
Captura de descripcion visual de suelos segun ASTM D2488 / USCS.
Funciona sin conexion: todo se guarda en SQLite local en el telefono.
"""

import os
import json

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.dropdown import DropDown
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.modalview import ModalView
from kivy.uix.widget import Widget
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle, Rectangle, Line
from kivy.utils import get_color_from_hex as hx

import db
import descripcion
import export_xlsx

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VOCAB_PATH = os.path.join(BASE_DIR, "vocab.json")

# ------------------------------------------------------------------
# Paleta de colores
# ------------------------------------------------------------------
NAVY = hx("#123A6B")          # azul JMF principal
NAVY_DARK = hx("#0B2748")     # azul presionado / textos fuertes
NAVY_SOFT = hx("#E6EEF8")     # azul muy claro (boton secundario)
NAVY_SOFT_DOWN = hx("#D2E0F1")
ACCENT = hx("#F2A541")        # ambar "tierra": acentos, avance
BG = hx("#EEF2F6")            # fondo general
CARD = hx("#FFFFFF")
INPUT_BG = hx("#F7F9FC")
BORDER = hx("#D3DBE5")
LABEL = hx("#3A4D63")
TEXT = hx("#15202B")
MUTED = hx("#8492A3")
HEADER_SUB = hx("#BFD3EA")
ERROR = hx("#D64545")
WHITE = hx("#FFFFFF")
SOMBRA = (0.05, 0.12, 0.22, 0.07)

SIN_DATO = "(sin dato)"
PLACEHOLDER_LISTA = "Seleccionar"

Window.clearcolor = BG
# En Android, sube el formulario para que el teclado no tape el campo activo
Window.softinput_mode = "below_target"


def cargar_vocab():
    with open(VOCAB_PATH, encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------
# Utilidades de dibujo
# ------------------------------------------------------------------
def fondo(widget, color, radio=12, borde=None, sombra=False):
    """Dibuja un fondo redondeado (opcionalmente con borde y sombra suave)
    detras del widget. Devuelve las instrucciones de color para poder
    cambiarlas despues (foco, error, boton presionado)."""
    ref = {}
    with widget.canvas.before:
        if sombra:
            Color(*SOMBRA)
            sombra_rect = RoundedRectangle(radius=[dp(radio)])
        ref["color"] = Color(*color)
        rect = RoundedRectangle(radius=[dp(radio)])
        if borde:
            ref["borde"] = Color(*borde)
            ref["linea"] = Line(width=dp(1))

    def actualizar(*_):
        x, y = widget.pos
        w, h = widget.size
        if sombra:
            sombra_rect.pos = (x, y - dp(3))
            sombra_rect.size = (w, h)
        rect.pos = (x, y)
        rect.size = (w, h)
        if borde:
            ref["linea"].rounded_rectangle = (x, y, w, h, dp(radio))

    widget.bind(pos=actualizar, size=actualizar)
    actualizar()
    return ref


def etiqueta(texto, tam="12.5sp", color=LABEL, negrita=False, halign="left", **kw):
    lbl = Label(text=texto, font_size=tam, color=color, bold=negrita,
                halign=halign, valign="middle", **kw)
    lbl.bind(size=lambda w, v: setattr(w, "text_size", v))
    return lbl


# ------------------------------------------------------------------
# Componentes
# ------------------------------------------------------------------
class BotonRedondo(Button):
    def __init__(self, texto, primario=True, **kw):
        super().__init__(text=texto, background_normal="", background_down="",
                         background_color=(0, 0, 0, 0), bold=True, font_size="15sp", **kw)
        self._normal = NAVY if primario else NAVY_SOFT
        self._presionado = NAVY_DARK if primario else NAVY_SOFT_DOWN
        self.color = WHITE if primario else NAVY
        self._f = fondo(self, self._normal, 12)
        self.bind(state=self._al_presionar)

    def _al_presionar(self, _w, estado):
        self._f["color"].rgba = self._presionado if estado == "down" else self._normal


class BarraProgreso(Widget):
    def __init__(self, **kw):
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", dp(6))
        super().__init__(**kw)
        self.valor = 0.0
        with self.canvas:
            Color(*NAVY_SOFT)
            self._fondo = RoundedRectangle(radius=[dp(3)])
            Color(*ACCENT)
            self._barra = RoundedRectangle(radius=[dp(3)])
        self.bind(pos=self._dibujar, size=self._dibujar)

    def fijar(self, valor):
        self.valor = max(0.0, min(1.0, valor))
        self._dibujar()

    def _dibujar(self, *_):
        self._fondo.pos = self.pos
        self._fondo.size = self.size
        self._barra.pos = self.pos
        self._barra.size = (max(self.height, self.width * self.valor) if self.valor > 0 else 0, self.height)


class CampoTexto(BoxLayout):
    """Etiqueta + caja de texto redondeada, con borde azul al enfocar."""
    def __init__(self, texto_etiqueta, al_cambiar=None, hint="", numerico=False, **kw):
        kw.setdefault("orientation", "vertical")
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", dp(76))
        kw.setdefault("spacing", dp(6))
        super().__init__(**kw)
        self.add_widget(etiqueta(texto_etiqueta, negrita=True, size_hint_y=None, height=dp(20)))

        self.caja = BoxLayout(size_hint_y=None, height=dp(48), padding=[dp(12), 0])
        self._f = fondo(self.caja, INPUT_BG, 10, borde=BORDER)
        self.input = TextInput(multiline=False, hint_text=hint, write_tab=False,
                               background_normal="", background_active="",
                               background_color=(0, 0, 0, 0), foreground_color=TEXT,
                               hint_text_color=MUTED, cursor_color=NAVY, cursor_width=dp(2),
                               font_size="15sp", padding=[0, dp(13), 0, dp(13)])
        if numerico:
            self.input.input_type = "number"
            self.input.input_filter = "float"
        self.input.bind(focus=self._al_enfocar)
        if al_cambiar:
            self.input.bind(text=lambda *_: al_cambiar())
        self.caja.add_widget(self.input)
        self.add_widget(self.caja)
        self._error = False

    def _al_enfocar(self, _w, enfocado):
        if enfocado:
            self.marcar_error(False)
        self._pintar_estado(enfocado)

    def _pintar_estado(self, enfocado=False):
        if self._error:
            self._f["borde"].rgba = ERROR
        else:
            self._f["borde"].rgba = NAVY if enfocado else BORDER
        self._f["color"].rgba = CARD if enfocado else INPUT_BG
        self._f["linea"].width = dp(1.6) if (enfocado or self._error) else dp(1)

    def marcar_error(self, error=True):
        self._error = error
        self._pintar_estado(self.input.focus)

    def limpiar(self):
        self.input.text = ""

    @property
    def value(self):
        return self.input.text.strip()


class OpcionLista(SpinnerOption):
    """Cada opcion del desplegable: fondo blanco, texto oscuro, alto comodo."""
    def __init__(self, **kw):
        super().__init__(**kw)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = WHITE
        self.color = TEXT
        self.font_size = "15sp"
        self.height = dp(48)
        self.halign = "left"
        self.valign = "middle"
        self.padding = [dp(16), 0, dp(16), 0]
        self.bind(size=lambda w, v: setattr(w, "text_size", v))
        self.bind(state=lambda w, s: setattr(w, "background_color", NAVY_SOFT if s == "down" else WHITE))
        with self.canvas.after:
            Color(*NAVY_SOFT)
            self._sep = Rectangle()
        self.bind(pos=self._linea, size=self._linea)

    def _linea(self, *_):
        self._sep.pos = (self.x + dp(12), self.y)
        self._sep.size = (self.width - dp(24), dp(1))


class ListaDesplegable(DropDown):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.max_height = dp(330)
        fondo(self, WHITE, 10, sombra=True)
        # borde por encima de las opciones para que se vea siempre
        with self.canvas.after:
            Color(*NAVY)
            self._borde = Line(width=dp(1.2))
        self.bind(pos=self._dibujar_borde, size=self._dibujar_borde)

    def _dibujar_borde(self, *_):
        self._borde.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(10))


class Selector(Spinner):
    """Spinner con placeholder, flecha dibujada y texto alineado a la izquierda."""
    def __init__(self, opciones, **kw):
        super().__init__(text=PLACEHOLDER_LISTA, values=[SIN_DATO] + list(opciones),
                         option_cls=OpcionLista, dropdown_cls=ListaDesplegable,
                         background_normal="", background_down="", background_color=(0, 0, 0, 0),
                         color=MUTED, font_size="15sp", halign="left", valign="middle",
                         shorten=True, shorten_from="right", padding=[0, 0, dp(28), 0], **kw)
        self.bind(size=lambda w, v: setattr(w, "text_size", v))
        self.bind(text=self._al_elegir)
        with self.canvas.after:
            self._c_flecha = Color(*MUTED)
            self._flecha = Line(width=dp(1.4), cap="round", joint="round")
        self.bind(pos=self._dibujar_flecha, size=self._dibujar_flecha)

    def _dibujar_flecha(self, *_):
        cx, cy, s = self.right - dp(10), self.center_y, dp(5)
        self._flecha.points = [cx - s, cy + s / 2, cx, cy - s / 2, cx + s, cy + s / 2]

    def _al_elegir(self, _w, texto):
        if texto == SIN_DATO or texto == "":
            self.text = PLACEHOLDER_LISTA
            return
        elegido = texto != PLACEHOLDER_LISTA
        self.color = TEXT if elegido else MUTED
        self._c_flecha.rgba = NAVY if elegido else MUTED

    def limpiar(self):
        self.text = PLACEHOLDER_LISTA

    @property
    def value(self):
        return "" if self.text == PLACEHOLDER_LISTA else self.text.strip()


class CampoLista(BoxLayout):
    """Etiqueta + selector redondeado (equivalente al desplegable del Excel)."""
    def __init__(self, texto_etiqueta, opciones, al_cambiar=None, **kw):
        kw.setdefault("orientation", "vertical")
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", dp(76))
        kw.setdefault("spacing", dp(6))
        super().__init__(**kw)
        self.add_widget(etiqueta(texto_etiqueta, negrita=True, size_hint_y=None, height=dp(20)))
        self.caja = BoxLayout(size_hint_y=None, height=dp(48), padding=[dp(12), 0, dp(8), 0])
        self._f = fondo(self.caja, INPUT_BG, 10, borde=BORDER)
        self.selector = Selector(opciones)
        self.spinner = self.selector  # alias (compatibilidad)
        self.selector.bind(is_open=self._al_abrir)
        if al_cambiar:
            self.selector.bind(text=lambda *_: al_cambiar())
        self.caja.add_widget(self.selector)
        self.add_widget(self.caja)

    def _al_abrir(self, _w, abierto):
        self._f["borde"].rgba = NAVY if abierto else BORDER
        self._f["linea"].width = dp(1.6) if abierto else dp(1)
        self._f["color"].rgba = CARD if abierto else INPUT_BG

    def limpiar(self):
        self.selector.limpiar()

    @property
    def value(self):
        return self.selector.value


class Seccion(BoxLayout):
    """Tarjeta blanca con numero, titulo y subtitulo."""
    def __init__(self, numero, titulo, subtitulo="", **kw):
        super().__init__(orientation="vertical", size_hint_y=None,
                         padding=[dp(16), dp(16), dp(16), dp(18)], spacing=dp(12), **kw)
        self.bind(minimum_height=self.setter("height"))
        fondo(self, CARD, 16, sombra=True)

        cabecera = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(12))
        ancla = AnchorLayout(size_hint_x=None, width=dp(30))
        insignia = Label(text=str(numero), bold=True, color=NAVY_DARK, font_size="14sp",
                         size_hint=(None, None), size=(dp(30), dp(30)))
        fondo(insignia, ACCENT, 15)
        ancla.add_widget(insignia)
        cabecera.add_widget(ancla)

        textos = BoxLayout(orientation="vertical")
        textos.add_widget(etiqueta(titulo, "15.5sp", TEXT, True))
        if subtitulo:
            textos.add_widget(etiqueta(subtitulo, "11.5sp", MUTED))
        cabecera.add_widget(textos)
        self.add_widget(cabecera)

        separador = Widget(size_hint_y=None, height=dp(1))
        with separador.canvas:
            Color(*NAVY_SOFT)
            linea = Rectangle()
        separador.bind(pos=lambda w, v: setattr(linea, "pos", v),
                       size=lambda w, v: setattr(linea, "size", v))
        self.add_widget(separador)


class Encabezado(BoxLayout):
    """Barra superior azul con el logotipo de JMF dibujado como texto
    (se ve nitido en cualquier resolucion de pantalla)."""
    def __init__(self, **kw):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(84),
                         padding=[dp(18), dp(12), dp(16), dp(14)], spacing=dp(14), **kw)
        with self.canvas.before:
            Color(*NAVY)
            self._fondo = Rectangle()
            Color(*ACCENT)
            self._linea = Rectangle()
        self.bind(pos=self._dibujar, size=self._dibujar)

        logo = BoxLayout(size_hint_x=None, width=dp(150), spacing=dp(6))
        logo.add_widget(Label(text="JMF", italic=True, bold=True, font_size="30sp",
                              color=WHITE, size_hint_x=None, width=dp(62)))
        sub = BoxLayout(orientation="vertical", padding=[0, dp(12), 0, dp(12)])
        sub.add_widget(etiqueta("INGENIERÍA &", "8.5sp", HEADER_SUB, True))
        sub.add_widget(etiqueta("CONSTRUCCIÓN", "8.5sp", HEADER_SUB, True))
        logo.add_widget(sub)
        self.add_widget(logo)

        divisor = Widget(size_hint_x=None, width=dp(1))
        with divisor.canvas:
            Color(1, 1, 1, 0.25)
            linea_div = Rectangle()
        divisor.bind(pos=lambda w, v: setattr(linea_div, "pos", (v[0], v[1] + dp(6))),
                     size=lambda w, v: setattr(linea_div, "size", (v[0], v[1] - dp(12))))
        self.add_widget(divisor)

        titulos = BoxLayout(orientation="vertical", padding=[0, dp(8), 0, dp(8)])
        titulos.add_widget(etiqueta("Bitácora geotécnica", "16sp", WHITE, True))
        titulos.add_widget(etiqueta("ASTM D2488 · USCS", "11.5sp", HEADER_SUB))
        self.add_widget(titulos)

    def _dibujar(self, *_):
        self._fondo.pos = self.pos
        self._fondo.size = self.size
        self._linea.pos = self.pos
        self._linea.size = (self.width, dp(3))


def mostrar_aviso(titulo, mensaje, error=False):
    vista = ModalView(size_hint=(0.86, None), height=dp(230), background="",
                      background_color=(0, 0, 0, 0), overlay_color=(0.04, 0.1, 0.18, 0.55))
    tarjeta = BoxLayout(orientation="vertical", padding=[dp(22), dp(20), dp(22), dp(18)],
                        spacing=dp(10))
    fondo(tarjeta, WHITE, 18)
    tarjeta.add_widget(etiqueta(titulo, "18sp", ERROR if error else NAVY, True,
                                size_hint_y=None, height=dp(28)))
    cuerpo = Label(text=mensaje, font_size="14sp", color=TEXT, halign="left", valign="top")
    cuerpo.bind(size=lambda w, v: setattr(w, "text_size", v))
    tarjeta.add_widget(cuerpo)
    boton = BotonRedondo("Entendido", True, size_hint_y=None, height=dp(46))
    boton.bind(on_release=lambda *_: vista.dismiss())
    tarjeta.add_widget(boton)
    vista.add_widget(tarjeta)
    vista.open()
    return vista


# ------------------------------------------------------------------
# Pantalla principal
# ------------------------------------------------------------------
class FormularioBitacora(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)
        with self.canvas.before:
            Color(*BG)
            self._bg = Rectangle()
        self.bind(pos=lambda w, v: setattr(self._bg, "pos", v),
                  size=lambda w, v: setattr(self._bg, "size", v))

        self.vocab = cargar_vocab()
        carpeta_datos = App.get_running_app().user_data_dir
        self.conn = db.conectar(os.path.join(carpeta_datos, "bitacora_local.db"))
        self.campos = {}

        self.add_widget(Encabezado())

        self.scroll = ScrollView(bar_width=dp(4), bar_color=(0.07, 0.23, 0.42, 0.35),
                                 bar_inactive_color=(0.07, 0.23, 0.42, 0.12), scroll_type=["bars", "content"])
        self.contenido = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(16),
                                   padding=[dp(14), dp(16), dp(14), dp(20)])
        self.contenido.bind(minimum_height=self.contenido.setter("height"))
        self.scroll.add_widget(self.contenido)
        self.add_widget(self.scroll)

        # 1. Identificacion
        s1 = self._seccion(1, "Identificación", "Proyecto y punto de investigación")
        self._texto(s1, "proyecto", "Nombre del proyecto", hint="Ej. Ampliación Planta Norte")
        self._texto(s1, "sondeo", "Sondeo / Pozo / Calicata", hint="Ej. C-01")

        # 2. Ubicacion y perforacion
        s2 = self._seccion(2, "Ubicación y perforación", "Coordenadas UTM y niveles en metros")
        self._doble(s2, ("coord_este", "Este (m)", "000000"), ("coord_norte", "Norte (m)", "0000000"))
        self._doble(s2, ("prof_desde", "Prof. desde (m)", "0.00"), ("prof_hasta", "Prof. hasta (m)", "0.00"))
        self._doble(s2, ("nivel_roca", "Nivel de roca (m)", "0.00"), ("nivel_agua", "Nivel de agua (m)", "0.00"))

        # 3. Clasificacion
        s3 = self._seccion(3, "Clasificación", "Grupo USCS y apariencia")
        self._lista(s3, "simbolo_uscs", "Símbolo USCS", "simbolo_uscs")
        self._texto(s3, "nombre_grupo", "Nombre de grupo (ASTM D2487)", hint="Ej. Arcilla arenosa")
        self._lista(s3, "color", "Color", "color")
        self._lista(s3, "humedad", "Humedad", "humedad")
        self._lista(s3, "consistencia_compacidad", "Consistencia / Compacidad", "consistencia_compacidad")

        # 4. Propiedades
        s4 = self._seccion(4, "Propiedades", "Ensayos manuales de campo")
        self._lista(s4, "plasticidad", "Plasticidad", "plasticidad")
        self._lista(s4, "resistencia_seca", "Resistencia en seco", "resistencia_seca")
        self._lista(s4, "dilatancia", "Dilatancia", "dilatancia")
        self._lista(s4, "tenacidad", "Tenacidad", "tenacidad")
        self._lista(s4, "estructura", "Estructura", "estructura")
        self._lista(s4, "forma_particulas", "Forma de partículas", "forma_particulas")
        self._lista(s4, "tamano_max_particula", "Tamaño máx. de partícula", "tamano_max_particula")
        self._lista(s4, "reaccion_hcl", "Reacción con HCl", "reaccion_hcl")
        self._lista(s4, "olor", "Olor", "olor")

        # 5. Observaciones
        s5 = self._seccion(5, "Observaciones", "Opcional")
        self._texto(s5, "formacion", "Formación geológica / Nombre local")
        self._texto(s5, "comentarios", "Comentarios adicionales")

        # Vista previa en vivo
        tarjeta_prev = BoxLayout(orientation="vertical", size_hint_y=None,
                                 padding=[dp(18), dp(16), dp(18), dp(18)], spacing=dp(8))
        tarjeta_prev.bind(minimum_height=tarjeta_prev.setter("height"))
        fondo(tarjeta_prev, NAVY, 16, sombra=True)
        tarjeta_prev.add_widget(etiqueta("VISTA PREVIA · DESCRIPCIÓN ASTM", "11sp", ACCENT, True,
                                         size_hint_y=None, height=dp(18)))
        self.preview = Label(text="", font_size="14sp", color=WHITE, halign="left",
                             valign="top", size_hint_y=None, line_height=1.25)
        self.preview.bind(width=lambda w, v: setattr(w, "text_size", (v, None)),
                          texture_size=lambda w, v: setattr(w, "height", v[1]))
        tarjeta_prev.add_widget(self.preview)
        self.contenido.add_widget(tarjeta_prev)

        # Barra inferior fija
        barra = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(142),
                          padding=[dp(16), dp(12), dp(16), dp(10)], spacing=dp(8))
        with barra.canvas.before:
            Color(*WHITE)
            fondo_barra = Rectangle()
            Color(*BORDER)
            borde_barra = Rectangle()
        barra.bind(pos=lambda w, v: (setattr(fondo_barra, "pos", v),
                                      setattr(borde_barra, "pos", (v[0], v[1] + w.height - dp(1)))),
                   size=lambda w, v: (setattr(fondo_barra, "size", v),
                                       setattr(borde_barra, "size", (v[0], dp(1))),
                                       setattr(borde_barra, "pos", (w.x, w.y + v[1] - dp(1)))))

        fila_avance = BoxLayout(size_hint_y=None, height=dp(18))
        self.lbl_avance = etiqueta("", "12sp", LABEL, True)
        self.lbl_pct = etiqueta("", "12sp", NAVY, True, halign="right", size_hint_x=0.3)
        fila_avance.add_widget(self.lbl_avance)
        fila_avance.add_widget(self.lbl_pct)
        barra.add_widget(fila_avance)
        self.progreso = BarraProgreso()
        barra.add_widget(self.progreso)

        botones = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        btn_guardar = BotonRedondo("Guardar registro", True)
        btn_guardar.bind(on_release=self.guardar)
        btn_exportar = BotonRedondo("Exportar Excel", False)
        btn_exportar.bind(on_release=self.exportar)
        botones.add_widget(btn_guardar)
        botones.add_widget(btn_exportar)
        barra.add_widget(botones)

        self.contador = etiqueta("", "11.5sp", MUTED, halign="center", size_hint_y=None, height=dp(18))
        barra.add_widget(self.contador)
        self.add_widget(barra)

        self._actualizar_contador()
        self._actualizar_vivo()

    # --- construccion ---
    def _seccion(self, numero, titulo, subtitulo):
        s = Seccion(numero, titulo, subtitulo)
        self.contenido.add_widget(s)
        return s

    def _texto(self, seccion, clave, texto, hint="", numerico=False, **kw):
        campo = CampoTexto(texto, al_cambiar=self._actualizar_vivo, hint=hint, numerico=numerico, **kw)
        self.campos[clave] = campo
        seccion.add_widget(campo)
        return campo

    def _doble(self, seccion, izq, der):
        fila = BoxLayout(size_hint_y=None, height=dp(76), spacing=dp(12))
        for clave, texto, hint in (izq, der):
            campo = CampoTexto(texto, al_cambiar=self._actualizar_vivo, hint=hint,
                               numerico=True, size_hint_y=1)
            self.campos[clave] = campo
            fila.add_widget(campo)
        seccion.add_widget(fila)

    def _lista(self, seccion, clave, texto, nombre_vocab):
        campo = CampoLista(texto, self.vocab[nombre_vocab], al_cambiar=self._actualizar_vivo)
        self.campos[clave] = campo
        seccion.add_widget(campo)
        return campo

    # --- estado en vivo ---
    def _leer_formulario(self):
        return {clave: campo.value for clave, campo in self.campos.items()}

    def _actualizar_vivo(self, *_):
        registro = self._leer_formulario()
        texto = descripcion.generar_descripcion(registro).rstrip(", ")
        self.preview.text = texto or ("Completa la clasificación y las propiedades: "
                                      "la descripción estándar se arma sola aquí.")
        self.preview.color = WHITE if texto else HEADER_SUB
        llenos = sum(1 for v in registro.values() if v)
        total = len(registro)
        self.lbl_avance.text = f"Avance del registro: {llenos} de {total} campos"
        self.lbl_pct.text = f"{round(100 * llenos / total)}%"
        self.progreso.fijar(llenos / total)

    def _actualizar_contador(self):
        total = len(db.listar_registros(self.conn))
        pendientes = len(db.listar_registros(self.conn, solo_no_sincronizados=True))
        palabra = "registro" if total == 1 else "registros"
        self.contador.text = f"{total} {palabra} en este teléfono  ·  {pendientes} sin exportar"

    def _preparar_siguiente_estrato(self):
        """Tras guardar, deja listos los datos del mismo pozo (proyecto,
        sondeo, coordenadas, niveles) y encadena la profundidad: el nuevo
        'desde' es el 'hasta' del estrato que se acaba de guardar."""
        conservar = {"proyecto", "sondeo", "coord_este", "coord_norte", "nivel_roca", "nivel_agua"}
        hasta_anterior = self.campos["prof_hasta"].value
        for clave, campo in self.campos.items():
            if clave not in conservar:
                campo.limpiar()
        self.campos["prof_desde"].input.text = hasta_anterior
        self.scroll.scroll_y = 1

    # --- acciones ---
    def guardar(self, *_):
        registro = self._leer_formulario()
        faltantes = [c for c in ("proyecto", "sondeo") if not registro.get(c)]
        if faltantes:
            for c in faltantes:
                self.campos[c].marcar_error(True)
            self.scroll.scroll_y = 1
            mostrar_aviso("Faltan datos", "Completa el nombre del proyecto y el sondeo / pozo "
                                          "antes de guardar.", error=True)
            return
        texto = descripcion.generar_descripcion(registro)
        tecnico = os.environ.get("USER", "Tecnico de campo")
        db.guardar_registro(self.conn, registro, tecnico=tecnico, descripcion=texto)
        desde, hasta = registro.get("prof_desde"), registro.get("prof_hasta")
        tramo = f"{desde} – {hasta} m" if (desde and hasta) else "sin profundidad indicada"
        self._preparar_siguiente_estrato()
        self._actualizar_contador()
        self._actualizar_vivo()
        mostrar_aviso("Registro guardado", f"{registro['sondeo']}  ·  {tramo}\n\n"
                                           "El formulario quedó listo para el siguiente estrato "
                                           "del mismo pozo.")

    def exportar(self, *_):
        registros = db.listar_registros(self.conn)
        if not registros:
            mostrar_aviso("Sin registros", "Todavía no hay registros guardados en este teléfono.",
                          error=True)
            return
        ruta = os.path.join(App.get_running_app().user_data_dir, "bitacora_exportada.xlsx")
        export_xlsx.exportar_a_xlsx(registros, ruta)
        db.marcar_sincronizados(self.conn, [r["id"] for r in registros])
        self._actualizar_contador()
        mostrar_aviso("Excel exportado", f"{len(registros)} registros exportados en:\n{ruta}\n\n"
                                         "Compártelo por WhatsApp, correo o Drive cuando tengas señal.")


class BitacoraApp(App):
    def build(self):
        self.title = "Bitácora Geotécnica JMF"
        return FormularioBitacora()


if __name__ == "__main__":
    BitacoraApp().run()
