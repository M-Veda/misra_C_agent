#pragma once

#include <map>
#include <string>
#include <vector>

namespace misra::clang {

struct ToolchainProfile {
    std::string id;
    std::string name;
    std::string compiler_family;
    std::string compiler_executable;
    std::string target_triple;
    std::string sysroot;
    std::string resource_directory;
    std::map<std::string, std::string> builtin_defines;
    std::vector<std::string> include_paths;
    std::vector<std::string> driver_extra_flags;
    std::vector<std::string> future_ready;
    std::string status;
};

struct DriverArgumentInput {
    std::string file_path;
    std::string working_directory;
    std::vector<std::string> compile_flags;
    std::map<std::string, std::string> defines;
    std::vector<std::string> include_paths;
    std::string target_triple;
    std::string toolchain_profile_id;
    std::string compiler_executable;
    std::string sysroot;
    std::string resource_directory;
};

class ToolchainProfileRegistry {
public:
    static ToolchainProfileRegistry& instance();

    bool loadFromDirectory(const std::string& directory);
    const ToolchainProfile* find(const std::string& profile_id) const;
    std::vector<std::string> listProfileIds() const;

private:
    std::map<std::string, ToolchainProfile> profiles_;
};

std::vector<std::string> buildDriverArguments(
    const DriverArgumentInput& input,
    const ToolchainProfile* profile);

}  // namespace misra::clang
