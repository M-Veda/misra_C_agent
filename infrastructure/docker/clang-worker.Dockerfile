FROM ubuntu:24.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    pkg-config \
    protobuf-compiler \
    protobuf-compiler-grpc \
    libprotobuf-dev \
    libgrpc++-dev \
    libgrpc-dev \
    clang-18 \
    llvm-18-dev \
    libclang-18-dev \
    libclang-cpp18-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY shared/contracts /build/shared/contracts
COPY shared/toolchain_profiles /build/shared/toolchain_profiles
COPY clang-worker /build/clang-worker

WORKDIR /build/clang-worker

RUN cmake -DCMAKE_BUILD_TYPE=Release -B build -S . && \
    cmake --build build --parallel $(nproc)

FROM ubuntu:24.04 AS production

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgrpc++1.51t64 \
    libgrpc29t64 \
    libprotobuf32t64 \
    libclang-cpp18 \
    clang-18 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /build/clang-worker/build/misra_clang_worker /app/misra_clang_worker
COPY --from=builder /build/shared/toolchain_profiles /app/toolchain_profiles
COPY infrastructure/scripts/healthcheck-clang.sh /app/healthcheck.sh
RUN chmod +x /app/healthcheck.sh /app/misra_clang_worker

EXPOSE 50051

CMD ["/app/misra_clang_worker", "--address", "0.0.0.0:50051", "--profile-dir", "/app/toolchain_profiles"]

FROM production AS development
