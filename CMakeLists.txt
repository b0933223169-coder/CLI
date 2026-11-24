cmake_minimum_required(VERSION 3.16)
project(coolqml LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_AUTOMOC ON)

set(CMAKE_PREFIX_PATH "C:/Qt/6.9.3/msvc2022_64")
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets Qml Quick QuickControls2 WebEngineWidgets WebEngineQuick WebChannel WebChannelQuick Network)
qt_standard_project_setup()

add_executable(coolqml WIN32
    main.cpp
    backend.cpp
    color_engine.cpp
    conpty.cpp
    qml_pty_bridge.cpp
    native.cpp
)
target_link_libraries(coolqml PRIVATE
    Qt6::Core Qt6::Gui Qt6::Widgets Qt6::Qml Qt6::Quick
    Qt6::QuickControls2 Qt6::WebEngineWidgets Qt6::WebEngineQuick Qt6::WebChannel Qt6::WebChannelQuick Qt6::Network Crypt32
)
target_include_directories(coolqml PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

