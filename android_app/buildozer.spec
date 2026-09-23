[app]
title = Bitacora Geotecnica
package.name = bitacorageotecnica
package.domain = org.tuempresa

source.dir = .
source.include_exts = py,json,jpg,jpeg,png

version = 1.0

# openpyxl es puro Python (no requiere compilacion nativa) -> funciona en p4a
requirements = python3==3.11.9,kivy==2.3.1,openpyxl,et_xmlfile,pillow

orientation = portrait
fullscreen = 0

# Permiso para poder compartir/guardar el Excel exportado (WhatsApp, correo, Drive)
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
