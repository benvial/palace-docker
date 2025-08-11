FROM rockylinux:9

ARG GIT_SHA
ARG CMAKE_VERSION=3.31.0


LABEL org.opencontainers.image.title="Palace" \
      org.opencontainers.image.source="https://github.com/awslabs/palace" \
      org.opencontainers.image.vendor="AWS Labs" \
      org.opencontainers.image.revision=$GIT_SHA \
      org.opencontainers.image.base.name="docker.io/library/rockylinux:9" \
      description="This container contains Palace compiled with all dependencies."

# Set build flags
ENV OPT_FLAGS="-O2"
ENV PATH="/opt/palace/bin:${PATH}"
ENV PATH="/usr/lib64/mpich/bin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/lib64/mpich/lib:${LD_LIBRARY_PATH:-}"


RUN mkdir -p /opt/palace-src

# Install dependencies
RUN dnf install -y dnf-plugins-core && \
    dnf config-manager --enable crb && \
    dnf install -y epel-release && \
    dnf update -y && \
    dnf groupinstall -y "Development Tools" && \
    dnf install -y curl-minimal gcc-gfortran git libunwind-devel openblas-devel \
                   pkg-config python3 wget zlib mpich-devel

# Install specific version of CMake
RUN wget https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/cmake-${CMAKE_VERSION}-linux-$(uname -m).sh && \
    bash cmake-${CMAKE_VERSION}-linux-*.sh --skip-license --prefix=/usr && \
    rm -f cmake-${CMAKE_VERSION}-linux-*.sh


# Clone Palace
RUN git clone https://github.com/awslabs/palace.git /opt/palace-src && \
    cd /opt/palace-src && \
    git checkout ${GIT_SHA}

# Build Palace
RUN mkdir -p /opt/palace-build && cd /opt/palace-build && \
    cmake /opt/palace-src \
        -DCMAKE_INSTALL_PREFIX=/opt/palace \
        -DCMAKE_CXX_COMPILER=g++ \
        -DCMAKE_CXX_FLAGS="${OPT_FLAGS}" \
        -DCMAKE_C_COMPILER=gcc \
        -DCMAKE_C_FLAGS="${OPT_FLAGS}" \
        -DCMAKE_Fortran_COMPILER=gfortran \
        -DCMAKE_Fortran_FLAGS="${OPT_FLAGS}" \
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
