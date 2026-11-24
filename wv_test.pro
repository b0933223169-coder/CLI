QT += qml quick network websockets
CONFIG += c++17 console
CONFIG -= app_bundle
SOURCES += wv_host.cpp pty_bridge.cpp conpty.cpp
HEADERS += pty_bridge.h conpty.h
INCLUDEPATH += .
