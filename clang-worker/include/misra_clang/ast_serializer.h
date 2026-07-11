#pragma once

#include "clang_analysis.pb.h"

#include <clang/AST/ASTContext.h>
#include <clang/AST/Decl.h>
#include <clang/AST/Stmt.h>
#include <clang/AST/Type.h>

#include <map>
#include <string>
#include <unordered_map>
#include <vector>

namespace misra::clang {

class AstSerializer {
public:
    explicit AstSerializer(clang::ASTContext& context);

    void serializeDecl(clang::Decl* declaration, v1::ParseTranslationUnitResponse* response);
    void finalize(v1::ParseTranslationUnitResponse* response);

private:
    clang::ASTContext& context_;
    std::unordered_map<std::string, std::string> decl_parent_map_;
    uint64_t node_counter_;

    std::string nextNodeId();
    v1::SourceRange makeSourceRange(clang::SourceRange range) const;
    v1::TypeInformation buildTypeInformation(clang::QualType type) const;
    std::string resolveEssentialType(clang::QualType type) const;
    std::vector<std::string> collectQualifiers(clang::QualType type) const;
    std::string getRawSpelling(clang::SourceRange range) const;
    uint32_t pointerNestingDepth(clang::QualType type) const;
    void enrichArrayMetadata(clang::QualType type, v1::TypeInformation* info) const;
    std::string linkageName(clang::Linkage linkage) const;
    std::string storageClassName(clang::StorageClass storage) const;

    void addNode(
        v1::ParseTranslationUnitResponse* response,
        const std::string& node_id,
        const std::string& parent_id,
        const std::string& kind,
        clang::SourceRange range,
        clang::QualType type,
        const std::map<std::string, std::string>& semantic_properties);

    void visitDecl(clang::Decl* declaration, const std::string& parent_id,
                   v1::ParseTranslationUnitResponse* response);
    void visitStmt(clang::Stmt* statement, const std::string& parent_id,
                   v1::ParseTranslationUnitResponse* response);
    void enrichDeclProperties(clang::Decl* declaration,
                              std::map<std::string, std::string>& properties) const;
    void enrichStmtProperties(clang::Stmt* statement,
                              std::map<std::string, std::string>& properties) const;
};

}  // namespace misra::clang
