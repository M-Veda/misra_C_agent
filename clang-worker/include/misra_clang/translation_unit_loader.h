#pragma once

#include "clang_analysis.pb.h"
#include "misra_clang/toolchain_profile.h"

#include <memory>
#include <string>

namespace misra::clang {

struct TranslationUnitResult {
    bool success = false;
    std::string status_message;
    std::string translation_unit_hash;
    uint64_t parse_duration_ms = 0;
    v1::ParseTranslationUnitResponse response;
};

class TranslationUnitLoader {
public:
    TranslationUnitResult parse(const DriverArgumentInput& input);
};

}  // namespace misra::clang
