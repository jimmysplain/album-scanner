[app]
title           = Album Scanner
package.name    = albumscanner
package.domain  = org.albumscanner
source.dir      = .
source.include_exts = py,png,jpg,kv,atlas,json
version         = 1.0.0

requirements = python3,kivy==2.3.0,pillow,requests,certifi,charset-normalizer,idna,urllib3,anyio,httpx,httpcore,sniffio,typing_extensions,pydantic,pydantic-core,anthropic,opencv

orientation     = portrait
fullscreen      = 0

android.minapi  = 24
android.api     = 34
android.ndk     = 25c
android.archs   = arm64-v8a

android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_VIDEO

android.allow_backup = True
android.logcat_filters = *:S python:D

[buildozer]
log_level = 2
warn_on_root = 1
