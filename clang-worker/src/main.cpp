#include "misra_clang/clang_analysis_service.h"
#include "misra_clang/health_service.h"
#include "misra_clang/toolchain_profile.h"

#include <grpcpp/grpcpp.h>
#include <grpcpp/health/v1/health.grpc.pb.h>

#include <iostream>
#include <memory>
#include <string>

namespace {

constexpr char kDefaultAddress[] = "0.0.0.0:50051";
constexpr char kDefaultProfileDirectory[] = "/app/toolchain_profiles";

std::string ParseAddress(int argc, char** argv) {
    for (int index = 1; index < argc; ++index) {
        const std::string argument = argv[index];
        if (argument == "--address" && index + 1 < argc) {
            return argv[index + 1];
        }
    }
    return kDefaultAddress;
}

std::string ParseProfileDirectory(int argc, char** argv) {
    for (int index = 1; index < argc; ++index) {
        const std::string argument = argv[index];
        if (argument == "--profile-dir" && index + 1 < argc) {
            return argv[index + 1];
        }
    }
    return kDefaultProfileDirectory;
}

bool IsHealthCheckMode(int argc, char** argv) {
    for (int index = 1; index < argc; ++index) {
        if (std::string(argv[index]) == "--health-check") {
            return true;
        }
    }
    return false;
}

int RunHealthCheck(const std::string& address) {
    auto channel = grpc::CreateChannel(address, grpc::InsecureChannelCredentials());
    auto stub = grpc::health::v1::Health::NewStub(channel);

    grpc::ClientContext context;
    grpc::health::v1::HealthCheckRequest request;
    grpc::health::v1::HealthCheckResponse response;

    request.set_service("");
    const grpc::Status status = stub->Check(&context, request, &response);
    if (!status.ok()) {
        std::cerr << "Health check RPC failed: " << status.error_message() << std::endl;
        return 1;
    }

    if (response.status() != grpc::health::v1::HealthCheckResponse::SERVING) {
        std::cerr << "Health check returned non-serving status." << std::endl;
        return 1;
    }

    return 0;
}

void RunServer(const std::string& address, const std::string& profile_directory) {
    if (!misra::clang::ToolchainProfileRegistry::instance().loadFromDirectory(profile_directory)) {
        std::cerr << "Failed to load toolchain profiles from " << profile_directory << std::endl;
        std::exit(1);
    }

    misra::clang::ClangAnalysisServiceImpl analysis_service;
    misra::clang::HealthServiceImpl health_service;

    grpc::ServerBuilder builder;
    builder.AddListeningPort(address, grpc::InsecureServerCredentials());
    builder.RegisterService(&analysis_service);
    builder.RegisterService(&health_service);

    std::unique_ptr<grpc::Server> server(builder.BuildAndStart());
    if (!server) {
        std::cerr << "Failed to start gRPC server on " << address << std::endl;
        std::exit(1);
    }

    std::cout << "misra-clang-worker listening on " << address << std::endl;
    server->Wait();
}

}  // namespace

int main(int argc, char** argv) {
    const std::string address = ParseAddress(argc, argv);

    if (IsHealthCheckMode(argc, argv)) {
        return RunHealthCheck(address);
    }

    RunServer(address, ParseProfileDirectory(argc, argv));
    return 0;
}
