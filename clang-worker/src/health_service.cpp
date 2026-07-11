#include "misra_clang/health_service.h"

namespace misra::clang {

grpc::Status HealthServiceImpl::Check(
    grpc::ServerContext* /*context*/,
    const grpc::health::v1::HealthCheckRequest* request,
    grpc::health::v1::HealthCheckResponse* response) {
    if (!request->service().empty() &&
        request->service() != "misra.clang.v1.ClangAnalysisService") {
        response->set_status(grpc::health::v1::HealthCheckResponse::NOT_FOUND);
        return grpc::Status::OK;
    }

    response->set_status(grpc::health::v1::HealthCheckResponse::SERVING);
    return grpc::Status::OK;
}

}  // namespace misra::clang
