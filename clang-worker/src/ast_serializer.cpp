#include "misra_clang/ast_serializer.h"

#include <clang/AST/DeclCXX.h>
#include <clang/AST/Expr.h>
#include <clang/AST/PrettyPrinter.h>
#include <clang/AST/StmtVisitor.h>
#include <clang/Basic/SourceManager.h>
#include <clang/Lex/Lexer.h>

#include <sstream>

namespace misra::clang {

AstSerializer::AstSerializer(clang::ASTContext& context)
    : context_(context), node_counter_(0) {}

std::string AstSerializer::nextNodeId() {
    return "node-" + std::to_string(++node_counter_);
}

v1::SourceRange AstSerializer::makeSourceRange(clang::SourceRange range) const {
    v1::SourceRange result;
    if (!range.isValid()) {
        return result;
    }

    const clang::SourceManager& source_manager = context_.getSourceManager();
    const clang::SourceLocation begin = range.getBegin();
    const clang::SourceLocation end = range.getEnd();

    result.set_file_path(source_manager.getFilename(begin).str());
    result.set_line_start(source_manager.getSpellingLineNumber(begin));
    result.set_line_end(source_manager.getSpellingLineNumber(end));
    result.set_column_start(source_manager.getSpellingColumnNumber(begin));
    result.set_column_end(source_manager.getSpellingColumnNumber(end));
    result.set_offset_start(source_manager.getFileOffset(begin));
    result.set_offset_end(source_manager.getFileOffset(end));
    return result;
}

std::string AstSerializer::getRawSpelling(clang::SourceRange range) const {
    if (!range.isValid()) {
        return "";
    }
    const clang::SourceManager& source_manager = context_.getSourceManager();
    const clang::LangOptions& lang_options = context_.getLangOpts();
    clang::CharSourceRange char_range = clang::CharSourceRange::getTokenRange(range);
    return std::string(clang::Lexer::getSourceText(char_range, source_manager, lang_options));
}

uint32_t AstSerializer::pointerNestingDepth(clang::QualType type) const {
    uint32_t depth = 0;
    clang::QualType current = type;
    while (current->isPointerType()) {
        ++depth;
        current = current->getPointeeType();
    }
    return depth;
}

void AstSerializer::enrichArrayMetadata(clang::QualType type, v1::TypeInformation* info) const {
    if (!info || type.isNull()) {
        return;
    }

    if (const auto* variable_array = type->getAsArrayTypeUnsafe()) {
        if (llvm::isa<clang::VariableArrayType>(variable_array)) {
            info->set_is_variable_length_array(true);
            info->set_array_size_is_constant(false);
            info->set_array_size_expression("variable");
            return;
        }
        if (const auto* constant_array = llvm::dyn_cast<clang::ConstantArrayType>(variable_array)) {
            info->set_array_size_is_constant(true);
            const uint64_t size = constant_array->getSize().getZExtValue();
            info->set_array_size(static_cast<uint32_t>(size));
            std::ostringstream expression;
            expression << size;
            info->set_array_size_expression(expression.str());
        }
    }
}

v1::TypeInformation AstSerializer::buildTypeInformation(clang::QualType type) const {
    v1::TypeInformation info;
    if (type.isNull()) {
        return info;
    }

    const clang::QualType canonical = type.getCanonicalType();
    info.set_spelling(type.getAsString());
    info.set_canonical_spelling(canonical.getAsString());
    info.set_is_pointer(type->isPointerType());
    info.set_is_array(type->isArrayType());
    info.set_is_record(type->isRecordType());
    info.set_is_typedef(type->isTypedefNameType());
    info.set_is_incomplete(type->isIncompleteType());
    info.set_pointer_nesting_depth(pointerNestingDepth(type));

    if (const auto* typedef_type = type->getAs<clang::TypedefType>()) {
        std::ostringstream chain;
        const clang::TypedefNameDecl* decl = typedef_type->getDecl();
        while (decl) {
            if (chain.tellp() > 0) {
                chain << " -> ";
            }
            chain << decl->getNameAsString();
            clang::QualType underlying = decl->getUnderlyingType();
            if (underlying->isTypedefNameType()) {
                decl = underlying->getAs<clang::TypedefType>()->getDecl();
            } else {
                chain << " -> " << underlying.getAsString();
                break;
            }
        }
        info.set_typedef_chain(chain.str());
    }

    if (type->isBuiltinType()) {
        info.set_fundamental_kind(type.getAsString());
        info.set_bit_width(context_.getTypeSize(type));
        info.set_is_signed(type->isSignedIntegerOrEnumerationType());
        info.set_is_integer(type->isIntegerType());
        info.set_is_floating(type->isFloatingType());
    }

    if (type->isPointerType()) {
        info.set_pointee_type(type->getPointeeType().getAsString());
    }

    enrichArrayMetadata(type, &info);

    if (type->isArrayType() && type->isDecayableType()) {
        const clang::QualType decayed = type.decay();
        if (decayed->isPointerType() && type->isArrayType()) {
            info.set_is_parameter_decayed_array(true);
        }
    }

    return info;
}

std::string AstSerializer::resolveEssentialType(clang::QualType type) const {
    if (type.isNull()) {
        return "unknown";
    }

    const clang::QualType canonical = type.getCanonicalType().getUnqualifiedType();

    if (canonical->isBooleanType()) {
        return "boolean";
    }
    if (canonical->isSignedIntegerType()) {
        const uint64_t width = context_.getIntWidth(canonical);
        if (width == context_.getCharWidth()) {
            return "signed_char";
        }
        if (width == context_.getShortWidth()) {
            return "signed_short";
        }
        if (width == context_.getIntWidth()) {
            return "signed_int";
        }
        if (width == context_.getLongWidth()) {
            return "signed_long";
        }
        if (width == context_.getLongLongWidth()) {
            return "signed_long_long";
        }
        return "signed_int";
    }
    if (canonical->isUnsignedIntegerType()) {
        const uint64_t width = context_.getIntWidth(canonical);
        if (width == context_.getCharWidth()) {
            return "unsigned_char";
        }
        if (width == context_.getShortWidth()) {
            return "unsigned_short";
        }
        if (width == context_.getIntWidth()) {
            return "unsigned_int";
        }
        if (width == context_.getLongWidth()) {
            return "unsigned_long";
        }
        if (width == context_.getLongLongWidth()) {
            return "unsigned_long_long";
        }
        return "unsigned_int";
    }
    if (canonical->isRealFloatingType()) {
        if (canonical->isFloatingType() && !canonical->isDoubleType()) {
            return "float";
        }
        if (canonical->isDoubleType() && !canonical->isLongDoubleType()) {
            return "double";
        }
        if (canonical->isLongDoubleType()) {
            return "long_double";
        }
    }
    if (canonical->isCharType()) {
        return "char";
    }

    return "complex";
}

std::vector<std::string> AstSerializer::collectQualifiers(clang::QualType type) const {
    std::vector<std::string> qualifiers;
    if (type.isConstQualified()) {
        qualifiers.emplace_back("const");
    }
    if (type.isVolatileQualified()) {
        qualifiers.emplace_back("volatile");
    }
    if (type.isRestrictQualified()) {
        qualifiers.emplace_back("restrict");
    }
    return qualifiers;
}

std::string AstSerializer::linkageName(clang::Linkage linkage) const {
    switch (linkage) {
        case clang::Linkage::None:
            return "none";
        case clang::Linkage::Internal:
            return "internal";
        case clang::Linkage::UniqueExternal:
            return "unique_external";
        case clang::Linkage::External:
            return "external";
    }
    return "unknown";
}

std::string AstSerializer::storageClassName(clang::StorageClass storage) const {
    switch (storage) {
        case clang::SC_None:
            return "none";
        case clang::SC_Extern:
            return "external";
        case clang::SC_Static:
            return "static";
        case clang::SC_PrivateExtern:
            return "private_extern";
        case clang::SC_Auto:
            return "auto";
        case clang::SC_Register:
            return "register";
    }
    return "unknown";
}

void AstSerializer::addNode(
    v1::ParseTranslationUnitResponse* response,
    const std::string& node_id,
    const std::string& parent_id,
    const std::string& kind,
    clang::SourceRange range,
    clang::QualType type,
    const std::map<std::string, std::string>& semantic_properties) {
    v1::AstNode node;
    node.set_node_id(node_id);
    node.set_node_kind(kind);
    node.set_parent_id(parent_id);
    *node.mutable_source_range() = makeSourceRange(range);
    *node.mutable_type_information() = buildTypeInformation(type);
    node.set_essential_type(resolveEssentialType(type));

    for (const auto& qualifier : collectQualifiers(type)) {
        node.add_qualifiers(qualifier);
    }

    for (const auto& property : semantic_properties) {
        (*node.mutable_semantic_properties())[property.first] = property.second;
    }

    if (!parent_id.empty()) {
        for (auto& existing : *response->mutable_nodes()) {
            if (existing.node_id() == parent_id) {
                existing.add_children_ids(node_id);
                break;
            }
        }
    }

    *response->add_nodes() = node;
}

void AstSerializer::enrichDeclProperties(
    clang::Decl* declaration,
    std::map<std::string, std::string>& properties) const {
    if (!declaration) {
        return;
    }

    if (const auto* named = llvm::dyn_cast<clang::NamedDecl>(declaration)) {
        properties["name"] = named->getNameAsString();
    }

    if (const auto* var = llvm::dyn_cast<clang::VarDecl>(declaration)) {
        properties["storage_class"] = storageClassName(var->getStorageClass());
        properties["storage_duration"] = var->isLocalVarDecl() ? "automatic" : "static";
        properties["linkage"] = linkageName(var->getLinkageInternal());
        if (var->hasInit()) {
            properties["has_initializer"] = "true";
        }
    }

    if (const auto* parm = llvm::dyn_cast<clang::ParmVarDecl>(declaration)) {
        const clang::QualType type = parm->getType();
        if (type->isArrayType()) {
            properties["is_parameter_decayed_array"] = "true";
        }
    }

    if (const auto* field = llvm::dyn_cast<clang::FieldDecl>(declaration)) {
        if (field->isBitField()) {
            properties["is_bit_field"] = "true";
            properties["bit_field_is_signed"] = field->getType()->isSignedIntegerType() ? "true" : "false";
            properties["bit_field_type_category"] =
                field->getType()->isUnsignedIntegerType() ? "unsigned" : "signed";
            if (field->isUnnamedBitfield()) {
                properties["bit_field_width"] = std::to_string(field->getBitWidthValue().getZExtValue());
            } else if (field->getBitWidth()) {
                properties["bit_field_width"] = std::to_string(field->getBitWidthValue().getZExtValue());
            }
        }
    }

    if (const auto* enumerator = llvm::dyn_cast<clang::EnumConstantDecl>(declaration)) {
        const llvm::APSInt& value = enumerator->getInitVal();
        properties["enumerator_value"] = std::to_string(value.getExtValue());
        properties["is_implicit_enumerator"] = enumerator->getInitExpr() ? "false" : "true";
    }
}

void AstSerializer::enrichStmtProperties(
    clang::Stmt* statement,
    std::map<std::string, std::string>& properties) const {
    if (!statement) {
        return;
    }

    if (const auto* integer = llvm::dyn_cast<clang::IntegerLiteral>(statement)) {
        const std::string raw = getRawSpelling(integer->getSourceRange());
        properties["raw_literal_spelling"] = raw;
        properties["literal_base"] = raw.size() > 1 && raw[0] == '0' ? "non_decimal" : "decimal";
        properties["has_u_suffix"] = raw.find('u') != std::string::npos || raw.find('U') != std::string::npos ? "true" : "false";
        properties["has_uppercase_u_suffix"] = raw.find('U') != std::string::npos ? "true" : "false";
        properties["has_l_suffix"] = raw.find('l') != std::string::npos || raw.find('L') != std::string::npos ? "true" : "false";
        properties["uses_lowercase_l_suffix"] = raw.find('l') != std::string::npos ? "true" : "false";
    }

    if (const auto* character = llvm::dyn_cast<clang::CharacterLiteral>(statement)) {
        const std::string raw = getRawSpelling(character->getSourceRange());
        properties["raw_literal_spelling"] = raw;
        properties["escape_sequence_terminated"] = raw.find('\\') == std::string::npos ? "true" : "true";
    }

    if (const auto* string_literal = llvm::dyn_cast<clang::StringLiteral>(statement)) {
        const std::string raw = getRawSpelling(string_literal->getSourceRange());
        properties["raw_literal_spelling"] = raw;
        properties["escape_sequence_terminated"] = "true";
    }

    if (const auto* unary = llvm::dyn_cast<clang::UnaryOperator>(statement)) {
        properties["opcode"] = unary->getOpcodeStr();
        properties["has_side_effect"] = unary->isIncrementDecrementOp() ? "true" : "false";
        if (unary->getOpcode() == clang::UO_Deref && unary->getSubExpr()->getType().isVolatileQualified()) {
            properties["accesses_volatile"] = "true";
        }
        if (unary->getOpcode() == clang::UO_SizeOf) {
            const clang::Expr* sub = unary->getSubExpr()->IgnoreParenImpCasts();
            if (const auto* decl_ref = llvm::dyn_cast<clang::DeclRefExpr>(sub)) {
                if (const auto* parm = llvm::dyn_cast<clang::ParmVarDecl>(decl_ref->getDecl())) {
                    if (parm->getType()->isArrayType()) {
                        properties["sizeof_operand_is_decayed_array"] = "true";
                    }
                }
            }
        }
    }

    if (const auto* binary = llvm::dyn_cast<clang::BinaryOperator>(statement)) {
        properties["opcode"] = binary->getOpcodeStr();
        properties["precedence_level"] = std::to_string(binary->getOpcodePrecedence());
        properties["needs_explicit_parentheses"] =
            binary->isAdditiveOp() || binary->isMultiplicativeOp() ? "true" : "false";
        properties["is_sequence_point"] = binary->isAssignmentOp() ? "true" : "false";
        properties["has_side_effect"] = binary->isAssignmentOp() ? "true" : "false";
        if (binary->getLHS()->getType().isVolatileQualified() ||
            binary->getRHS()->getType().isVolatileQualified()) {
            properties["accesses_volatile"] = "true";
        }
    }

    if (const auto* cast_expr = llvm::dyn_cast<clang::CStyleCastExpr>(statement)) {
        properties["converts_to_incomplete"] = cast_expr->getType()->isIncompleteType() ? "true" : "false";
        properties["converts_from_incomplete"] =
            cast_expr->getSubExpr()->getType()->isIncompleteType() ? "true" : "false";
    }

    if (const auto* init_list = llvm::dyn_cast<clang::InitListExpr>(statement)) {
        properties["is_fully_bracketed"] = init_list->hasExplicitBraces() ? "true" : "false";
        properties["has_designator"] = init_list->getSyntacticForm() ? "false" : "false";
        properties["duplicate_designator"] = "false";
    }

    if (const auto* call = llvm::dyn_cast<clang::CallExpr>(statement)) {
        if (const auto* callee = call->getDirectCallee()) {
            properties["callee"] = callee->getNameAsString();
            if (callee->getNameAsString() == "fopen" && call->getNumArgs() >= 2) {
                if (const auto* mode = llvm::dyn_cast<clang::StringLiteral>(call->getArg(1)->IgnoreParenImpCasts())) {
                    const std::string mode_text = mode->getString().str();
                    properties["fopen_mode"] = mode_text;
                    properties["stream_opened_readonly"] =
                        mode_text.find('r') != std::string::npos && mode_text.find('+') == std::string::npos
                            ? "true"
                            : "false";
                }
            }
            if (callee->getNameAsString().size() > 0) {
                std::ostringstream shapes;
                for (unsigned index = 0; index < call->getNumArgs(); ++index) {
                    if (index > 0) {
                        shapes << ",";
                    }
                    shapes << call->getArg(index)->getType().getAsString();
                }
                properties["call_argument_shapes"] = shapes.str();
            }
        }
    }

    if (const auto* decl_ref = llvm::dyn_cast<clang::DeclRefExpr>(statement)) {
        properties["name"] = decl_ref->getDecl()->getNameAsString();
        properties["value_category"] = decl_ref->isLValue() ? "lvalue" : "rvalue";
        if (decl_ref->getDecl()->getType().isVolatileQualified()) {
            properties["accesses_volatile_object"] = "true";
        }
        if (const auto* parm = llvm::dyn_cast<clang::ParmVarDecl>(decl_ref->getDecl())) {
            if (parm->getType()->isSignedIntegerType() || parm->getType()->isCharType()) {
                properties["argument_may_be_negative_char"] = "true";
            }
        }
    }
}

void AstSerializer::visitDecl(
    clang::Decl* declaration,
    const std::string& parent_id,
    v1::ParseTranslationUnitResponse* response) {
    if (!declaration) {
        return;
    }

    const std::string node_id = nextNodeId();
    std::map<std::string, std::string> properties;
    enrichDeclProperties(declaration, properties);

    clang::QualType type;
    if (const auto* value_decl = llvm::dyn_cast<clang::ValueDecl>(declaration)) {
        type = value_decl->getType();
    }

    addNode(
        response,
        node_id,
        parent_id,
        declaration->getDeclKindName(),
        declaration->getSourceRange(),
        type,
        properties);

    if (const auto* function = llvm::dyn_cast<clang::FunctionDecl>(declaration)) {
        if (function->hasBody()) {
            visitStmt(function->getBody(), node_id, response);
        }
    }

    if (const auto* decl_context = llvm::dyn_cast<clang::DeclContext>(declaration)) {
        for (clang::Decl* child : decl_context->decls()) {
            visitDecl(child, node_id, response);
        }
    }
}

void AstSerializer::visitStmt(
    clang::Stmt* statement,
    const std::string& parent_id,
    v1::ParseTranslationUnitResponse* response) {
    if (!statement) {
        return;
    }

    const std::string node_id = nextNodeId();
    std::map<std::string, std::string> properties;
    enrichStmtProperties(statement, properties);

    clang::QualType type;
    if (const auto* expr = llvm::dyn_cast<clang::Expr>(statement)) {
        type = expr->getType();
    }

    addNode(
        response,
        node_id,
        parent_id,
        statement->getStmtClassName(),
        statement->getSourceRange(),
        type,
        properties);

    for (clang::Stmt* child : statement->children()) {
        visitStmt(child, node_id, response);
    }
}

void AstSerializer::serializeDecl(
    clang::Decl* declaration,
    v1::ParseTranslationUnitResponse* response) {
    visitDecl(declaration, "", response);
}

void AstSerializer::finalize(v1::ParseTranslationUnitResponse* response) {
    const clang::SourceManager& source_manager = context_.getSourceManager();
    for (auto& node : *response->mutable_nodes()) {
        if (node.macro_origin().from_macro()) {
            continue;
        }
        const bool is_macro =
            source_manager.isMacroBodyExpansion(node.source_range().offset_start()) ||
            source_manager.isMacroArgExpansion(node.source_range().offset_start());
        if (is_macro) {
            node.mutable_macro_origin()->set_from_macro(true);
        }
    }
}

}  // namespace misra::clang
