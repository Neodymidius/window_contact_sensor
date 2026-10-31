# Define minimal required version of CMake.
cmake_minimum_required(VERSION "3.25")

# Project definition
project(
	ZigbeeWindowContactSensor
	VERSION 0.1.0
	LANGUAGES C CXX ASM
)

# Include the definition of the slc_ZigbeeWindowContactSensor target,
# which contains the content of the SLC project
include(ZigbeeWindowContactSensor.cmake)

# IAS Zone token headers include "config/ias-zone-server-config.h".
target_include_directories(slc PUBLIC "${CMAKE_CURRENT_LIST_DIR}/..")

# Support the added ADC component before the next full Studio regeneration.
# After regeneration the SDK source is already part of slc.
get_target_property(contact_sdk_sources slc SOURCES)
if(NOT "${contact_sdk_sources}" MATCHES "/em_iadc\\.c")
    target_sources(slc PRIVATE "../simplicity_sdk_2026.6.2/platform_core/platform/emlib/src/em_iadc.c")
endif()

add_executable(ZigbeeWindowContactSensor
    # Add additional sources here
)

target_include_directories(ZigbeeWindowContactSensor PUBLIC
    # Add additional include paths here
)

target_compile_definitions(ZigbeeWindowContactSensor PUBLIC
    # Add additional macros here
)

target_compile_options(ZigbeeWindowContactSensor PUBLIC
    # Set additional compiler flags here
)

target_link_options(ZigbeeWindowContactSensor PUBLIC
    # Set additional linker flags here
)

# Link with the content defined in the SLC project
target_link_libraries(ZigbeeWindowContactSensor PRIVATE
    slc
)

# Include managed project content if available
include(ZigbeeWindowContactSensor_project.cmake OPTIONAL RESULT_VARIABLE managed_project)
if(managed_project)
    message(STATUS "Using managed project content from ${managed_project}")
endif()

# Force the gcc linker command
set_target_properties(ZigbeeWindowContactSensor PROPERTIES LINKER_LANGUAGE C)

# Create .bin, .hex and .s37 artifacts after building the project
add_custom_command(TARGET ZigbeeWindowContactSensor
    POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} ${OBJCOPY_SREC_CMD} "$<TARGET_FILE:ZigbeeWindowContactSensor>" "$<TARGET_FILE_DIR:ZigbeeWindowContactSensor>/$<TARGET_FILE_BASE_NAME:ZigbeeWindowContactSensor>.s37"
    COMMAND ${CMAKE_OBJCOPY} ${OBJCOPY_IHEX_CMD} "$<TARGET_FILE:ZigbeeWindowContactSensor>" "$<TARGET_FILE_DIR:ZigbeeWindowContactSensor>/$<TARGET_FILE_BASE_NAME:ZigbeeWindowContactSensor>.hex"
    COMMAND ${CMAKE_OBJCOPY} ${OBJCOPY_BIN_CMD}  "$<TARGET_FILE:ZigbeeWindowContactSensor>" "$<TARGET_FILE_DIR:ZigbeeWindowContactSensor>/$<TARGET_FILE_BASE_NAME:ZigbeeWindowContactSensor>.bin" 
)

# Run post-build pipeline to perform additional post-processing
if(post_build_command)
add_custom_command(TARGET ZigbeeWindowContactSensor
    POST_BUILD
    WORKING_DIRECTORY ${CMAKE_CURRENT_LIST_DIR}/..
    COMMAND ${post_build_command}
)
endif()
