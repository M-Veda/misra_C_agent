#pragma once

#include <grpcpp/grpcpp.h>
#include <grpcpp/health/v1/health.grpc.pb.h>

namespace misra::clang {

class HealthServiceImpl final
    : public grpc::health::v1::Health::Service {
public:
    grpc::Status Check(
        grpc::ServerContext* context,
        const grpc::health::v1::HealthCheckRequest* request,
        grpc::health::v1::HealthCheckResponse* response) override;
};

}  // namespace misra::clang
