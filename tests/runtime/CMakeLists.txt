cmake_minimum_required(VERSION 3.20)
project(RoPlasmaSetupProbe LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_AUTOMOC ON)
find_package(ECM 6.26 REQUIRED NO_MODULE)
list(APPEND CMAKE_MODULE_PATH ${ECM_MODULE_PATH})
include(KDEInstallDirs6)
include(ECMQmlModule)
find_package(Qt6 6.10 REQUIRED COMPONENTS Core Gui Qml Quick Test)
find_package(KF6Package 6.26 REQUIRED)
qt_policy(SET QTP0004 NEW)

if(NOT EXISTS "${PLASMA_SETUP_SOURCE}/src/components/setupmodule.cpp")
    message(FATAL_ERROR "Set PLASMA_SETUP_SOURCE to tools/harness.py prepare's verified source directory")
endif()
# This builds only the unchanged, pure upstream component, never the application,
# boot utilities, account backends, privileged helpers or built-in pages.
add_subdirectory("${PLASMA_SETUP_SOURCE}/src/components" upstream-components)
add_executable(ro-plasma-probe main.cpp)
target_link_libraries(ro-plasma-probe PRIVATE Qt6::Quick Qt6::Qml Qt6::Test KF6::Package
    componentsplugin componentspluginplugin)
# No install() rule: the runner and upstream static plugin stay in the build tree.
