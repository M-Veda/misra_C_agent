#pragma once

#include "clang_analysis.pb.h"

#include <clang/Lex/PPCallbacks.h>
#include <clang/Basic/SourceManager.h>

#include <string>
#include <vector>

namespace misra::clang {

class PreprocessorTracker : public clang::PPCallbacks {
public:
    PreprocessorTracker(
        clang::SourceManager& source_manager,
        v1::PreprocessorMetadata* output);

    void MacroDefined(
        const clang::Token& macro_name_token,
        const clang::MacroDirective* macro_directive) override;

    void MacroExpands(
        const clang::Token& macro_name_token,
        const clang::MacroDefinition& macro_definition,
        clang::SourceRange range,
        const clang::MacroArgs* args) override;

    void InclusionDirective(
        clang::SourceLocation hash_loc,
        const clang::Token& include_token,
        llvm::StringRef file_name,
        bool is_angled,
        clang::CharSourceRange filename_range,
        clang::OptionalFileEntryRef file,
        llvm::StringRef search_path,
        llvm::StringRef relative_path,
        const clang::Module* suggested_module,
        bool module_import,
        clang::SrcMgr::CharacteristicKind file_type) override;

    void If(clang::SourceLocation loc, clang::SourceRange condition_range,
            ConditionValueKind condition_value) override;

    void Elif(clang::SourceLocation loc, clang::SourceRange condition_range,
              ConditionValueKind condition_value, clang::SourceLocation if_loc) override;

    void Ifdef(clang::SourceLocation loc, const clang::Token& macro_name_token,
               const clang::MacroDefinition& macro_definition) override;

    void Ifndef(clang::SourceLocation loc, const clang::Token& macro_name_token,
                const clang::MacroDefinition& macro_definition) override;

    void MacroUndefined(
        const clang::Token& macro_name_token,
        const clang::MacroDefinition& macro_definition,
        const clang::SourceRange& range) override;

    void PragmaDirective(
        clang::SourceLocation location,
        clang::PragmaIntroducerKind introducer,
        clang::StringRef pragma_name,
        clang::StringRef pragma_value) override;

private:
    clang::SourceManager& source_manager_;
    v1::PreprocessorMetadata* output_;

    void captureMacroBodyTokens(const clang::MacroInfo* info, v1::MacroDefinition* definition) const;

    v1::SourceRange makeSourceRange(clang::SourceRange range) const;
    v1::SourceRange makeSourceRange(clang::CharSourceRange range) const;
    std::string getSpelling(clang::SourceLocation location) const;
};

}  // namespace misra::clang
