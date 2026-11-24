QT += qml quick quickcontrols2

CONFIG += c++17
CONFIG -= console
QMAKE_CXXFLAGS += -DWIN32
CONFIG -= app_bundle

SOURCES += main.cpp backend.cpp color_engine.cpp conpty.cpp term_buffer.cpp
HEADERS += backend.h color_engine.h conpty.h term_buffer.h

# Qt 版本由呼叫的 qmake 決定（build.bat 用 MinGW 版 qmake）
