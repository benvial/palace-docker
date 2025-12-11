FROM ubuntu:latest

ARG VERSION
ARG GITHUB_TOKEN

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
        cmake \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Configure git to use GitHub token for authenticated requests
RUN if [ -n "$GITHUB_TOKEN" ]; then \
        git config --global url."https://${GITHUB_TOKEN}@github.com/".insteadOf "https://github.com/" ; \
    fi

# Configure curl to add Authorization header for GitHub requests
RUN if [ -n "$GITHUB_TOKEN" ]; then \
        mkdir -p ~/.curlrc.d && \
        echo 'header = "Authorization: token '${GITHUB_TOKEN}'"' > /root/.curlrc ; \
    fi

# Add retry logic for wget and curl
RUN echo "tries = 5" >> /etc/wgetrc && \
    echo "waitretry = 2" >> /etc/wgetrc && \
    echo "timeout = 30" >> /etc/wgetrc && \
    echo "retry = 5" >> /root/.curlrc && \
    echo "retry-delay = 2" >> /root/.curlrc && \
    echo "connect-timeout = 30" >> /root/.curlrc

# Clone Palace
RUN git clone https://github.com/awslabs/palace.git /opt/palace-src  && \
    cd /opt/palace-src && \
    git checkout ${VERSION}

# Build Palace with CMake configured to use authentication
RUN mkdir -p /opt/palace-build && cd /opt/palace-build && \
    if [ -n "$GITHUB_TOKEN" ]; then \
        CMAKE_EXTRA_ARGS="-DCMAKE_TLS_VERIFY=ON" ; \
    else \
        CMAKE_EXTRA_ARGS="" ; \
    fi && \
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
        -DPALACE_WITH_GSLIB:BOOL=ON \
        ${CMAKE_EXTRA_ARGS} && \
    make -j"$(nproc)" && \
    cd / && rm -rf /opt/palace-build

# Clear credentials after build (security best practice)
RUN git config --global --unset url."https://${GITHUB_TOKEN}@github.com/".insteadOf || true && \
    rm -f /root/.curlrc

CMD ["/bin/bash"]