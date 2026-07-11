cmake_minimum_required(VERSION 3.22)
project(misra_clang_worker VERSION 1.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Protobuf REQUIRED)
find_package(gRPC REQUIRED)

set(LLVM_DIR "/usr/lib/llvm-18/lib/cmake/llvm" CACHE PATH "LLVM cmake directory")
set(Clang_DIR "/usr/lib/llvm-18/lib/cmake/clang" CACHE PATH "Clang cmake directory")
find_package(LLVM 18 REQUIRED CONFIG)
find_package(Clang 18 REQUIRED CONFIG)

message(STATUS "Found LLVM ${LLVM_PACKAGE_VERSION}")
message(STATUS "Found Clang ${CLANG_PACKAGE_VERSION}")

llvm_map_components_to_libnames(LLVM_LIBS support)
set(CLANG_LIBS
    clangAST
    clangBasic
    clangDriver
    clangFrontend
    clangLex
    clangParse
    clangSema
    clangSerialization
    clangTooling
)

set(PROTO_FILE "${CMAKE_CURRENT_SOURCE_DIR}/../shared/contracts/clang_analysis.proto")
set(GENERATED_DIR "${CMAKE_BINARY_DIR}/generated")
file(MAKE_DIRECTORY "${GENERATED_DIR}")

set(PROTO_SRCS "${GENERATED_DIR}/clang_analysis.pb.cc")
set(PROTO_HDRS "${GENERATED_DIR}/clang_analysis.pb.h")
set(GRPC_SRCS "${GENERATED_DIR}/clang_analysis.grpc.pb.cc")
set(GRPC_HDRS "${GENERATED_DIR}/clang_analysis.grpc.pb.h")

add_custom_command(
    OUTPUT ${PROTO_SRCS} ${PROTO_HDRS} ${GRPC_SRCS} ${GRPC_HDRS}
    COMMAND protobuf::protoc
    ARGS
        --proto_path=${CMAKE_CURRENT_SOURCE_DIR}/../shared/contracts
        --cpp_out=${GENERATED_DIR}
        --grpc_out=${GENERATED_DIR}
        --plugin=protoc-gen-grpc=$<TARGET_FILE:gRPC::grpc_cpp_plugin>
        ${PROTO_FILE}
    DEPENDS ${PROTO_FILE}
    COMMENT "Generating gRPC sources from clang_analysis.proto"
)

add_library(clang_analysis_proto STATIC ${PROTO_SRCS} ${GRPC_SRCS})
target_include_directories(clang_analysis_proto PUBLIC ${GENERATED_DIR})
target_link_libraries(clang_analysis_proto PUBLIC protobuf::libprotobuf gRPC::grpc++)

add_executable(misra_clang_worker
    src/main.cpp
    src/clang_analysis_service.cpp
    src/health_service.cpp
    src/toolchain_profile.cpp
    src/preprocessor_tracker.cpp
    src/ast_serializer.cpp
    src/translation_unit_loader.cpp
)

target_include_directories(misra_clang_worker PRIVATE
    ${GENERATED_DIR}
    include
    ${LLVM_INCLUDE_DIRS}
    ${CLANG_INCLUDE_DIRS}
)

target_compile_definitions(misra_clang_worker PRIVATE ${LLVM_DEFINITIONS})

target_link_libraries(misra_clang_worker PRIVATE
    clang_analysis_proto
    gRPC::grpc++
    protobuf::libprotobuf
    ${CLANG_LIBS}
    ${LLVM_LIBS}
)

install(TARGETS misra_clang_worker RUNTIME DESTINATION bin)
