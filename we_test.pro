QMAKE_MSC_VER = 1944
QT += core gui widgets webenginewidgets webchannel
CONFIG += c++17 console
CONFIG -= app_bundle
SOURCES += we_host.cpp conpty.cpp
HEADERS += conpty.h
INCLUDEPATH += .
