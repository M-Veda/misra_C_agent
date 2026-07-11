#include "misra_clang/preprocessor_tracker.h"

#include <clang/Basic/SourceManager.h>
#include <clang/Lex/MacroInfo.h>
#include <clang/Lex/Token.h>

#include <sstream>

namespace misra::clang {

PreprocessorTracker::PreprocessorTracker(
    clang::SourceManager& source_manager,
    v1::PreprocessorMetadata* output)
    : source_manager_(source_manager), output_(output) {}

v1::SourceRange PreprocessorTracker::makeSourceRange(clang::SourceRange range) const {
    v1::SourceRange result;
    if (!range.isValid()) {
        return result;
    }

    const clang::SourceLocation begin = range.getBegin();
    const clang::SourceLocation end = range.getEnd();

    result.set_file_path(source_manager_.getFilename(begin).str());
    result.set_line_start(source_manager_.getSpellingLineNumber(begin));
    result.set_line_end(source_manager_.getSpellingLineNumber(end));
    result.set_column_start(source_manager_.getSpellingColumnNumber(begin));
    result.set_column_end(source_manager_.getSpellingColumnNumber(end));
    result.set_offset_start(source_manager_.getFileOffset(begin));
    result.set_offset_end(source_manager_.getFileOffset(end));
    return result;
}

v1::SourceRange PreprocessorTracker::makeSourceRange(clang::CharSourceRange range) const {
    return makeSourceRange(range.getAsRange());
}

std::string PreprocessorTracker::getSpelling(clang::SourceLocation location) const {
    if (!location.isValid()) {
        return "";
    }
    return source_manager_.getCharacterData(location);
}

void PreprocessorTracker::MacroDefined(
    const clang::Token& macro_name_token,
    const clang::MacroDirective* macro_directive) {
    if (!output_ || !macro_directive) {
        return;
    }

    const clang::MacroInfo* info = macro_directive->getMacroInfo();
    if (!info) {
        return;
    }

    v1::MacroDefinition definition;
    definition.set_name(macro_name_token.getIdentifierInfo()->getName().str());
    definition.set_is_function_like(info->isFunctionLike());
    definition.set_file_path(
        source_manager_.getFilename(info->getDefinitionLoc()).str());

    if (info->isObjectLike()) {
        const clang::SourceRange replacement_range = info->getReplacementTokenRange();
        if (replacement_range.isValid()) {
            definition.set_value(getSpelling(replacement_range.getBegin()));
        }
    }

    captureMacroBodyTokens(info, &definition);

    *definition.mutable_range() = makeSourceRange(info->getDefinitionLoc());
    *output_->add_macro_definitions() = definition;
}

void PreprocessorTracker::captureMacroBodyTokens(
    const clang::MacroInfo* info,
    v1::MacroDefinition* definition) const {
    if (!info || !definition) {
        return;
    }

    bool uses_stringify = false;
    bool uses_token_paste = false;

    for (const clang::Token& token : info->tokens()) {
        v1::MacroBodyToken body_token;
        body_token.set_kind(std::to_string(static_cast<int>(token.getKind())));
        body_token.set_spelling(token.getName());
        *definition->add_body_tokens() = body_token;

        if (token.getKind() == clang::tok::hash) {
            uses_stringify = true;
        }
        if (token.getKind() == clang::tok::hashhash) {
            uses_token_paste = true;
        }
    }

    definition->set_uses_stringify(uses_stringify);
    definition->set_uses_token_paste(uses_token_paste);
}

void PreprocessorTracker::MacroUndefined(
    const clang::Token& macro_name_token,
    const clang::MacroDefinition& /*macro_definition*/,
    const clang::SourceRange& range) {
    if (!output_) {
        return;
    }

    v1::UndefDirective undef;
    undef.set_macro_name(macro_name_token.getIdentifierInfo()->getName().str());
    *undef.mutable_range() = makeSourceRange(range);
    *output_->add_undef_directives() = undef;
}

void PreprocessorTracker::PragmaDirective(
    clang::SourceLocation location,
    clang::PragmaIntroducerKind /*introducer*/,
    clang::StringRef pragma_name,
    clang::StringRef pragma_value) {
    if (!output_) {
        return;
    }

    v1::PragmaDirective pragma;
    std::ostringstream text;
    text << pragma_name.str();
    if (!pragma_value.empty()) {
        text << " " << pragma_value.str();
    }
    pragma.set_pragma_text(text.str());
    *pragma.mutable_range() = makeSourceRange(location);
    *output_->add_pragma_directives() = pragma;
}

void PreprocessorTracker::MacroExpands(
    const clang::Token& macro_name_token,
    const clang::MacroDefinition& macro_definition,
    clang::SourceRange range,
    const clang::MacroArgs* args) {
    if (!output_) {
        return;
    }

    v1::MacroExpansion expansion;
    expansion.set_name(macro_name_token.getIdentifierInfo()->getName().str());
    *expansion.mutable_use_range() = makeSourceRange(range);

    if (macro_definition.getMacroInfo()) {
        expansion.set_replacement(
            getSpelling(macro_definition.getMacroInfo()->getDefinitionLoc()));
        *expansion.mutable_definition_range() =
            makeSourceRange(macro_definition.getMacroInfo()->getDefinitionLoc());
    }

    expansion.add_chain(expansion.name());
    *output_->add_macro_expansions() = expansion;
}

void PreprocessorTracker::InclusionDirective(
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
    clang::SrcMgr::CharacteristicKind file_type) {
    if (!output_) {
        return;
    }

    v1::IncludeDirective directive;
    directive.set_included_file(file_name.str());
    directive.set_is_system(is_angled);
    *directive.mutable_range() = makeSourceRange(filename_range);

    if (file) {
        directive.set_resolved_path(file->getName().str());
    } else if (!search_path.empty()) {
        directive.set_resolved_path((search_path + relative_path).str());
    }

    *output_->add_include_directives() = directive;
}

void PreprocessorTracker::If(
    clang::SourceLocation loc,
    clang::SourceRange condition_range,
    ConditionValueKind condition_value) {
    if (!output_) {
        return;
    }

    v1::ConditionalBranch branch;
    branch.set_directive("if");
    branch.set_taken(condition_value == CVK_True);
    branch.set_condition(getSpelling(condition_range.getBegin()));
    *branch.mutable_range() = makeSourceRange(condition_range);
    *output_->add_conditional_branches() = branch;
}

void PreprocessorTracker::Elif(
    clang::SourceLocation loc,
    clang::SourceRange condition_range,
    ConditionValueKind condition_value,
    clang::SourceLocation if_loc) {
    if (!output_) {
        return;
    }

    v1::ConditionalBranch branch;
    branch.set_directive("elif");
    branch.set_taken(condition_value == CVK_True);
    branch.set_condition(getSpelling(condition_range.getBegin()));
    *branch.mutable_range() = makeSourceRange(condition_range);
    *output_->add_conditional_branches() = branch;
}

void PreprocessorTracker::Ifdef(
    clang::SourceLocation loc,
    const clang::Token& macro_name_token,
    const clang::MacroDefinition& macro_definition) {
    if (!output_) {
        return;
    }

    v1::ConditionalBranch branch;
    branch.set_directive("ifdef");
    branch.set_taken(macro_definition.getMacroInfo() != nullptr);
    branch.set_condition(macro_name_token.getIdentifierInfo()->getName().str());
    *branch.mutable_range() = makeSourceRange(loc);
    *output_->add_conditional_branches() = branch;
}

void PreprocessorTracker::Ifndef(
    clang::SourceLocation loc,
    const clang::Token& macro_name_token,
    const clang::MacroDefinition& macro_definition) {
    if (!output_) {
        return;
    }

    v1::ConditionalBranch branch;
    branch.set_directive("ifndef");
    branch.set_taken(macro_definition.getMacroInfo() == nullptr);
    branch.set_condition(macro_name_token.getIdentifierInfo()->getName().str());
    *branch.mutable_range() = makeSourceRange(loc);
    *output_->add_conditional_branches() = branch;
}

void PreprocessorTracker::Endif(clang::SourceLocation loc, clang::SourceLocation if_loc) {
    if (!output_) {
        return;
    }

    v1::ConditionalBranch branch;
    branch.set_directive("endif");
    *branch.mutable_range() = makeSourceRange(loc);
    *output_->add_conditional_branches() = branch;
}

}  // namespace misra::clang
