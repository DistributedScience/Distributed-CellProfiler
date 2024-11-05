#
#                                 - [ BROAD'16 ] -
#
# A docker instance for accessing AWS resources
# This wraps the cellprofiler docker registry
#


FROM cellprofiler/cellprofiler:4.2.8

# Install S3FS

RUN apt-get -y update           && \
    apt-get -y upgrade          && \
    apt-get -y install 		\
	automake 		\
	autotools-dev 		\
	g++ 			\
	git 			\
  jq 			\
	libcurl4-gnutls-dev 	\
	libfuse-dev 		\
	libssl-dev 		\
	libxml2-dev 		\
	make pkg-config		\
	sysstat			\
	curl

RUN apt-get install --only-upgrade bash

WORKDIR /usr/local/src
RUN git clone https://github.com/s3fs-fuse/s3fs-fuse.git
WORKDIR /usr/local/src/s3fs-fuse
RUN ./autogen.sh
RUN ./configure
RUN make
RUN make install

# Install AWS CLI

RUN apt install unzip
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN unzip awscliv2.zip
RUN ./aws/install

# Install boto3

RUN python3.8 -m pip install boto3

# Install watchtower for logging

RUN python3.8 -m pip install watchtower

# Install pandas for optional file downloading

RUN python3.8 -m pip install pandas

# SETUP NEW ENTRYPOINT

RUN mkdir -p /home/ubuntu/
WORKDIR /home/ubuntu
COPY cp-worker.py .
COPY instance-monitor.py .
COPY run-worker.sh .
RUN chmod 755 run-worker.sh

RUN git clone https://github.com/CellProfiler/CellProfiler-plugins.git
WORKDIR /home/ubuntu/CellProfiler-plugins
#RUN pip install -r requirements.txt

WORKDIR /home/ubuntu
ENTRYPOINT ["./run-worker.sh"]
CMD [""]
