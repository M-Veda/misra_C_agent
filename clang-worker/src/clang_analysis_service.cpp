#include "misra_clang/clang_analysis_service.h"
#include "misra_clang/translation_unit_loader.h"
#include "misra_clang/toolchain_profile.h"

#include <clang/Config/config.h>
#include <llvm/Config/llvm-config.h>

#include <chrono>
#include <sstream>

namespace misra::clang {

namespace {

constexpr char kServiceName[] = "misra-clang-worker";
constexpr char kServiceVersion[] = "1.2.0";
constexpr uint32_t kAstSchemaVersion = 3;

grpc::Status InvalidArgument(const std::string& field, const std::string& reason) {
    return grpc::Status(grpc::StatusCode::INVALID_ARGUMENT, field + ": " + reason);
}

DriverArgumentInput toDriverInput(const v1::ParseTranslationUnitRequest& request) {
    DriverArgumentInput input;
    input.file_path = request.file_path();
    input.working_directory = request.working_directory();
    input.compile_flags = {request.compile_flags().begin(), request.compile_flags().end()};
    input.include_paths = {request.include_paths().begin(), request.include_paths().end()};
    input.target_triple = request.target_triple();
    input.toolchain_profile_id = request.toolchain_profile_id();
    input.compiler_executable = request.compiler_executable();
    input.sysroot = request.sysroot();
    input.resource_directory = request.resource_directory();
    for (const auto& entry : request.defines()) {
        input.defines.emplace(entry.first, entry.second);
    }
    return input;
}

}  // namespace

grpc::Status ClangAnalysisServiceImpl::ParseTranslationUnit(
    grpc::ServerContext* /*context*/,
    const v1::ParseTranslationUnitRequest* request,
    v1::ParseTranslationUnitResponse* response) {
    if (request->file_path().empty()) {
        return InvalidArgument("file_path", "must not be empty");
    }

    TranslationUnitLoader loader;
    const TranslationUnitResult result = loader.parse(toDriverInput(*request));

    *response = result.response;
    response->set_ast_schema_version(kAstSchemaVersion);

    if (!result.success) {
        return grpc::Status::OK;
    }

    std::ostringstream translation_unit_id;
    translation_unit_id << result.translation_unit_hash << ":" << request->file_path();
    response->set_translation_unit_id(translation_unit_id.str());
    return grpc::Status::OK;
}

grpc::Status ClangAnalysisServiceImpl::GetServiceInfo(
    grpc::ServerContext* /*context*/,
    const v1::GetServiceInfoRequest* /*request*/,
    v1::GetServiceInfoResponse* response) {
    response->set_service_name(kServiceName);
    response->set_version(kServiceVersion);
    response->set_ast_schema_version(kAstSchemaVersion);
    response->set_ready(true);
    response->set_llvm_version(LLVM_VERSION_STRING);
    response->set_clang_version(CLANG_VERSION_STRING);

    for (const auto& profile_id : ToolchainProfileRegistry::instance().listProfileIds()) {
        response->add_supported_profiles(profile_id);
    }

    return grpc::Status::OK;
}

}  // namespace misra::clang
