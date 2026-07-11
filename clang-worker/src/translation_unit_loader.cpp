#include "misra_clang/translation_unit_loader.h"

#include "misra_clang/ast_serializer.h"
#include "misra_clang/preprocessor_tracker.h"
#include "misra_clang/toolchain_profile.h"

#include <clang/AST/ASTConsumer.h>
#include <clang/Frontend/CompilerInstance.h>
#include <clang/Frontend/FrontendAction.h>
#include <clang/Tooling/CompilationDatabase.h>
#include <clang/Tooling/Tooling.h>
#include <llvm/Support/SHA256.h>

#include <chrono>
#include <memory>
#include <sstream>

namespace misra::clang {

namespace {

class CaptureAstConsumer : public clang::ASTConsumer {
public:
    CaptureAstConsumer(
        clang::CompilerInstance& compiler_instance,
        v1::ParseTranslationUnitResponse* response)
        : compiler_instance_(compiler_instance), response_(response) {}

    void HandleTranslationUnit(clang::ASTContext& context) override {
        AstSerializer serializer(context);
        for (auto* declaration : context.getTranslationUnitDecl()->decls()) {
            if (declaration->getLocation().isInvalid()) {
                continue;
            }
            serializer.serializeDecl(declaration, response_);
        }
        serializer.finalize(response_);
        appendDiagnostics(compiler_instance_.getDiagnostics(), response_);
    }

private:
    clang::CompilerInstance& compiler_instance_;
    v1::ParseTranslationUnitResponse* response_;
};

class CaptureAstAction : public clang::ASTFrontendAction {
public:
    explicit CaptureAstAction(v1::ParseTranslationUnitResponse* response)
        : response_(response) {}

protected:
    std::unique_ptr<clang::ASTConsumer> CreateASTConsumer(
        clang::CompilerInstance& compiler_instance,
        llvm::StringRef) override {
        compiler_instance.getPreprocessor().addPPCallbacks(
            std::make_unique<PreprocessorTracker>(
                compiler_instance.getSourceManager(),
                response_->mutable_preprocessor()));
        return std::make_unique<CaptureAstConsumer>(compiler_instance, response_);
    }

private:
    v1::ParseTranslationUnitResponse* response_;
};

class CaptureAstActionFactory : public clang::tooling::FrontendActionFactory {
public:
    explicit CaptureAstActionFactory(v1::ParseTranslationUnitResponse* response)
        : response_(response) {}

    std::unique_ptr<clang::FrontendAction> create() override {
        return std::make_unique<CaptureAstAction>(response_);
    }

private:
    v1::ParseTranslationUnitResponse* response_;
};

std::string computeHash(const std::vector<std::string>& arguments, const std::string& file_path) {
    llvm::SHA256 hasher;
    for (const auto& argument : arguments) {
        hasher.update(argument);
        hasher.update('\0');
    }
    hasher.update(file_path);
    const auto digest = hasher.final();
    llvm::SmallString<64> hex_output;
    llvm::toHex(digest, /*LowerCase=*/true, hex_output);
    return hex_output.str().str();
}

void appendDiagnostics(
    clang::DiagnosticsEngine& diagnostics,
    v1::ParseTranslationUnitResponse* response) {
    const unsigned count = diagnostics.getNumDiagnostics();
    for (unsigned index = 0; index < count; ++index) {
        const clang::Diagnostic& diagnostic = diagnostics.getDiagnostic(index);
        if (diagnostic.getLevel() < clang::DiagnosticsEngine::Warning) {
            continue;
        }

        v1::DiagnosticMessage message;
        switch (diagnostic.getLevel()) {
            case clang::DiagnosticsEngine::Warning:
                message.set_severity("warning");
                break;
            case clang::DiagnosticsEngine::Error:
            case clang::DiagnosticsEngine::Fatal:
                message.set_severity("error");
                break;
            default:
                message.set_severity("note");
                break;
        }

        message.set_message(diagnostic.getMessage().str());
        message.set_category(std::to_string(diagnostic.getID()));

        const clang::SourceManager* source_manager = diagnostic.getSourceManager();
        if (source_manager && diagnostic.getLocation().isValid()) {
            v1::SourceRange range;
            range.set_file_path(source_manager->getFilename(diagnostic.getLocation()).str());
            range.set_line_start(source_manager->getSpellingLineNumber(diagnostic.getLocation()));
            range.set_column_start(source_manager->getSpellingColumnNumber(diagnostic.getLocation()));
            *message.mutable_range() = range;
        }

        *response->add_diagnostics() = message;
    }
}

}  // namespace

TranslationUnitResult TranslationUnitLoader::parse(const DriverArgumentInput& input) {
    TranslationUnitResult result;
    result.response.set_file_path(input.file_path);
    result.response.set_ast_schema_version(2);

    const ToolchainProfile* profile = nullptr;
    if (!input.toolchain_profile_id.empty()) {
        profile = ToolchainProfileRegistry::instance().find(input.toolchain_profile_id);
        if (!profile) {
            result.success = false;
            result.status_message = "Unknown toolchain profile: " + input.toolchain_profile_id;
            result.response.set_success(false);
            result.response.set_status_message(result.status_message);
            return result;
        }
        if (profile->status == "profile_ready_parsing_deferred") {
            result.success = false;
            result.status_message =
                "Toolchain profile '" + profile->id +
                "' is future-ready; Clang replay parsing is not enabled yet.";
            result.response.set_success(false);
            result.response.set_status_message(result.status_message);
            return result;
        }
    }

    const std::vector<std::string> arguments = buildDriverArguments(input, profile);
    result.translation_unit_hash = computeHash(arguments, input.file_path);

    std::vector<std::string> compile_flags;
    compile_flags.reserve(arguments.size());
    for (size_t index = 1; index + 1 < arguments.size(); ++index) {
        compile_flags.push_back(arguments[index]);
    }

    const auto started = std::chrono::steady_clock::now();

    const std::string working_directory = input.working_directory.empty()
        ? "."
        : input.working_directory;

    auto compilation_database = std::make_unique<clang::tooling::FixedCompilationDatabase>(
        working_directory,
        compile_flags);

    clang::tooling::ClangTool tool(*compilation_database, {input.file_path});
    CaptureAstActionFactory factory(&result.response);
    const int exit_code = tool.run(&factory);

    const auto finished = std::chrono::steady_clock::now();
    result.parse_duration_ms = static_cast<uint64_t>(
        std::chrono::duration_cast<std::chrono::milliseconds>(finished - started).count());

    if (exit_code != 0 && result.response.nodes().empty()) {
        result.success = false;
        result.status_message = "Clang frontend failed with exit code " + std::to_string(exit_code);
        result.response.set_success(false);
        result.response.set_status_message(result.status_message);
        result.response.set_translation_unit_hash(result.translation_unit_hash);
        result.response.set_parse_duration_ms(result.parse_duration_ms);
        return result;
    }

    result.success = true;
    result.status_message = "Translation unit parsed successfully.";
    result.response.set_success(true);
    result.response.set_status_message(result.status_message);
    result.response.set_translation_unit_hash(result.translation_unit_hash);
    result.response.set_parse_duration_ms(result.parse_duration_ms);
    return result;
}

}  // namespace misra::clang
