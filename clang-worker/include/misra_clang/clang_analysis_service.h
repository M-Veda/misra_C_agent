#pragma once

#include <grpcpp/grpcpp.h>

#include "clang_analysis.grpc.pb.h"

namespace misra::clang {

class ClangAnalysisServiceImpl final
    : public misra::clang::v1::ClangAnalysisService::Service {
public:
    grpc::Status ParseTranslationUnit(
        grpc::ServerContext* context,
        const v1::ParseTranslationUnitRequest* request,
        v1::ParseTranslationUnitResponse* response) override;

    grpc::Status GetServiceInfo(
        grpc::ServerContext* context,
        const v1::GetServiceInfoRequest* request,
        v1::GetServiceInfoResponse* response) override;
};

}  // namespace misra::clang
