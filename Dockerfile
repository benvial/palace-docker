FROM ubuntu:22.04

ARG VERSION

LABEL org.opencontainers.image.title="Palace" \
      org.opencontainers.image.source="https://github.com/awslabs/palace" \
      org.opencontainers.image.vendor="AWS Labs" \
      org.opencontainers.image.revision=$VERSION \
      org.opencontainers.image.base.name="docker.io/library/ubuntu:22.04" \
      description="This container contains Palace compiled with all dependencies."

ENV PATH="/opt/palace/bin:${PATH}"

RUN mkdir -p /opt/palace-src

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        gcc \
        g++ \
        gfortran \
        git \
        libunwind-dev \
        libopenblas-dev \
        pkg-config \
        python3 \
        wget \
        zlib1g-dev \
        mpich \
        libmpich-dev \
        ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*


# Palace needs CMake ≥ 3.26
RUN wget https://github.com/Kitware/CMake/releases/download/v3.31.0/cmake-3.31.0-linux-$(uname -m).sh && \
    bash cmake-3.31.0-linux-*.sh --skip-license --prefix=/usr/local && \
    rm -f cmake-3.31.0-linux-*.sh



# Clone Palace
RUN git clone https://github.com/awslabs/palace.git /opt/palace-src  && \
    cd /opt/palace-src && \
    git checkout ${VERSION}

# Build Palace
RUN mkdir -p /opt/palace-build && cd /opt/palace-build && \
    cmake /opt/palace-src \
        -DCMAKE_INSTALL_PREFIX=/opt/palace \
        -DCMAKE_BUILD_TYPE="Release" \
        -DCMAKE_CXX_COMPILER=g++ \
        -DCMAKE_C_COMPILER=gcc \
        -DCMAKE_Fortran_COMPILER=gfortran \
        -DBUILD_SHARED_LIBS:BOOL=ON \
        -DPALACE_WITH_64BIT_INT:BOOL=OFF \
        -DPALACE_WITH_OPENMP:BOOL=ON \
        -DPALACE_WITH_CUDA:BOOL=OFF \
        -DPALACE_WITH_HIP:BOOL=OFF \
        -DPALACE_WITH_SUPERLU:BOOL=ON \
        -DPALACE_WITH_STRUMPACK:BOOL=ON \
        -DPALACE_WITH_MUMPS:BOOL=ON \
        -DPALACE_WITH_SLEPC:BOOL=ON \
        -DPALACE_WITH_ARPACK:BOOL=ON \
        -DPALACE_WITH_LIBXSMM:BOOL=ON \
        -DPALACE_WITH_MAGMA:BOOL=ON \
        -DPALACE_WITH_GSLIB:BOOL=ON && \
    make -j"$(nproc)" && \
    cd / && rm -rf /opt/palace-build

CMD ["/bin/bash"]
