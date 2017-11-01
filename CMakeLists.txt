cmake_minimum_required(VERSION 3.7)
# 3.7 is required for SOURCE_SUBDIR External_cleaver.cmake

project(SegmentMesher)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/lassoan/SlicerSegmentMesher")
set(EXTENSION_CATEGORY "Segmentation")
set(EXTENSION_CONTRIBUTORS "Andras Lasso (PerkLab, Queen's University)")
set(EXTENSION_DESCRIPTION "Create volumetric mesh from segmentation using Cleaver2 or TetGen.")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/lassoan/SlicerSegmentMesher/master/SlicerSegmentMesher.png")
set(EXTENSION_SCREENSHOTURLS "https://raw.githubusercontent.com/lassoan/SlicerSegmentMesher/master/Screenshot01.jpg")
set(EXTENSION_DEPENDS "NA") # Specified as a space separated string, a list or 'NA' if any
set(EXTENSION_BUILD_SUBDIRECTORY inner-build)

set(SUPERBUILD_TOPLEVEL_PROJECT inner)

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})
mark_as_superbuild(Slicer_DIR)

find_package(Git REQUIRED)
mark_as_superbuild(GIT_EXECUTABLE)

#-----------------------------------------------------------------------------
# SuperBuild setup
option(${EXTENSION_NAME}_SUPERBUILD "Build ${EXTENSION_NAME} and the projects it depends on." ON)
mark_as_advanced(${EXTENSION_NAME}_SUPERBUILD)
if(${EXTENSION_NAME}_SUPERBUILD)
  include("${CMAKE_CURRENT_SOURCE_DIR}/SuperBuild.cmake")
  return()
endif()

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(SegmentMesher)
## NEXT_MODULE

#-----------------------------------------------------------------------------
#  install directory, install project name, install component, and install subdirectory.
set(CPACK_INSTALL_CMAKE_PROJECTS "${CPACK_INSTALL_CMAKE_PROJECTS};${CMAKE_BINARY_DIR};${EXTENSION_NAME};ALL;/")
set(CPACK_INSTALL_CMAKE_PROJECTS "${CPACK_INSTALL_CMAKE_PROJECTS};${tetgen_DIR};tetgen;RuntimeLibraries;/")
set(CPACK_INSTALL_CMAKE_PROJECTS "${CPACK_INSTALL_CMAKE_PROJECTS};${cleaver_DIR};CLEAVER2;RuntimeCLI;/")
MESSAGE(STATUS "CPACK_INSTALL_CMAKE_PROJECTS = ${CPACK_INSTALL_CMAKE_PROJECTS}") 

include(${Slicer_EXTENSION_CPACK})
