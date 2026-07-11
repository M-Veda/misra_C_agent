#include "misra_clang/toolchain_profile.h"

#include <llvm/Support/JSON.h>
#include <llvm/Support/MemoryBuffer.h>

#include <filesystem>
#include <fstream>
#include <sstream>

namespace misra::clang {

namespace {

std::vector<std::string> readStringArray(const llvm::json::Value& value) {
    std::vector<std::string> result;
    if (const auto* array = value.getAsArray()) {
        for (const auto& item : *array) {
            if (const auto* string_value = item.getAsString()) {
                result.emplace_back(string_value->str());
            }
        }
    }
    return result;
}

std::map<std::string, std::string> readStringMap(const llvm::json::Value& value) {
    std::map<std::string, std::string> result;
    if (const auto* object = value.getAsObject()) {
        for (const auto& entry : *object) {
            if (const auto* string_value = entry.second.getAsString()) {
                result.emplace(entry.first.str(), string_value->str());
            }
        }
    }
    return result;
}

ToolchainProfile parseProfile(const llvm::json::Object& object) {
    ToolchainProfile profile;
    if (const auto* value = object.get("id")) {
        if (const auto* string_value = value->getAsString()) {
            profile.id = string_value->str();
        }
    }
    if (const auto* value = object.get("name")) {
        if (const auto* string_value = value->getAsString()) {
            profile.name = string_value->str();
        }
    }
    if (const auto* value = object.get("compiler_family")) {
        if (const auto* string_value = value->getAsString()) {
            profile.compiler_family = string_value->str();
        }
    }
    if (const auto* value = object.get("compiler_executable")) {
        if (const auto* string_value = value->getAsString()) {
            profile.compiler_executable = string_value->str();
        }
    }
    if (const auto* value = object.get("target_triple")) {
        if (const auto* string_value = value->getAsString()) {
            profile.target_triple = string_value->str();
        }
    }
    if (const auto* value = object.get("sysroot")) {
        if (const auto* string_value = value->getAsString()) {
            profile.sysroot = string_value->str();
        }
    }
    if (const auto* value = object.get("resource_directory")) {
        if (const auto* string_value = value->getAsString()) {
            profile.resource_directory = string_value->str();
        }
    }
    if (const auto* value = object.get("status")) {
        if (const auto* string_value = value->getAsString()) {
            profile.status = string_value->str();
        }
    }
    if (const auto* value = object.get("builtin_defines")) {
        profile.builtin_defines = readStringMap(*value);
    }
    if (const auto* value = object.get("include_paths")) {
        profile.include_paths = readStringArray(*value);
    }
    if (const auto* value = object.get("driver_extra_flags")) {
        profile.driver_extra_flags = readStringArray(*value);
    }
    if (const auto* value = object.get("future_ready")) {
        profile.future_ready = readStringArray(*value);
    }
    return profile;
}

}  // namespace

ToolchainProfileRegistry& ToolchainProfileRegistry::instance() {
    static ToolchainProfileRegistry registry;
    return registry;
}

bool ToolchainProfileRegistry::loadFromDirectory(const std::string& directory) {
    namespace fs = std::filesystem;
    if (!fs::exists(directory)) {
        return false;
    }

    for (const auto& entry : fs::directory_iterator(directory)) {
        if (!entry.is_regular_file() || entry.path().extension() != ".json") {
            continue;
        }

        auto buffer = llvm::MemoryBuffer::getFile(entry.path().string());
        if (!buffer) {
            continue;
        }

        auto parsed = llvm::json::parse(buffer.get()->getBuffer());
        if (!parsed) {
            continue;
        }

        if (const auto* object = parsed->getAsObject()) {
            ToolchainProfile profile = parseProfile(*object);
            if (!profile.id.empty()) {
                profiles_[profile.id] = profile;
            }
        }
    }

    return !profiles_.empty();
}

const ToolchainProfile* ToolchainProfileRegistry::find(const std::string& profile_id) const {
    const auto iterator = profiles_.find(profile_id);
    if (iterator == profiles_.end()) {
        return nullptr;
    }
    return &iterator->second;
}

std::vector<std::string> ToolchainProfileRegistry::listProfileIds() const {
    std::vector<std::string> ids;
    ids.reserve(profiles_.size());
    for (const auto& entry : profiles_) {
        ids.push_back(entry.first);
    }
    return ids;
}

std::vector<std::string> buildDriverArguments(
    const DriverArgumentInput& input,
    const ToolchainProfile* profile) {
    std::vector<std::string> arguments;

    const std::string compiler = !input.compiler_executable.empty()
        ? input.compiler_executable
        : (profile ? profile->compiler_executable : "clang");
    arguments.push_back(compiler);
    arguments.push_back("-fsyntax-only");

    if (profile) {
        for (const auto& flag : profile->driver_extra_flags) {
            arguments.push_back(flag);
        }
    }

    for (const auto& flag : input.compile_flags) {
        arguments.push_back(flag);
    }

    const std::string target_triple = !input.target_triple.empty()
        ? input.target_triple
        : (profile ? profile->target_triple : "");
    if (!target_triple.empty()) {
        arguments.push_back("--target=" + target_triple);
    }

    const std::string sysroot = !input.sysroot.empty()
        ? input.sysroot
        : (profile ? profile->sysroot : "");
    if (!sysroot.empty()) {
        arguments.push_back("--sysroot=" + sysroot);
    }

    const std::string resource_dir = !input.resource_directory.empty()
        ? input.resource_directory
        : (profile ? profile->resource_directory : "");
    if (!resource_dir.empty()) {
        arguments.push_back("-resource-dir=" + resource_dir);
    }

    if (profile) {
        for (const auto& include_path : profile->include_paths) {
            arguments.push_back("-I" + include_path);
        }
        for (const auto& define : profile->builtin_defines) {
            arguments.push_back("-D" + define.first + "=" + define.second);
        }
    }

    for (const auto& include_path : input.include_paths) {
        arguments.push_back("-I" + include_path);
    }

    for (const auto& define : input.defines) {
        arguments.push_back("-D" + define.first + "=" + define.second);
    }

    arguments.push_back(input.file_path);
    return arguments;
}

}  // namespace misra::clang
