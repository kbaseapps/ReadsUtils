FROM kbase/sdkpython:3.8.10
MAINTAINER KBase Developer
# -----------------------------------------

# Insert apt-get instructions here to install
# any required dependencies for your module.

RUN mkdir -p /opt/lib

RUN apt-get update \
    && apt-get install -y g++ libz-dev wget nano tree

RUN wget -O /opt/lib/FastaValidator-1.0.jar https://github.com/kbase/jars/raw/master/lib/jars/FastaValidator/FastaValidator-1.0.jar

RUN pip install ipython==5.3.0 pyftpdlib==1.5.6


RUN cd /opt \
    && git clone https://github.com/statgen/libStatGen.git \
    && cd libStatGen \
    && make

RUN cd /opt \
    && git clone https://github.com/statgen/fastQValidator.git \
    && cd fastQValidator \
    && make

ENV PATH $PATH:/opt/fastQValidator/bin/

# -----------------------------------------

COPY ./ /kb/module
RUN mkdir -p /kb/module/work
RUN chmod -R a+rw /kb/module

WORKDIR /kb/module

RUN make all

ENTRYPOINT [ "./scripts/entrypoint.sh" ]

CMD [ ]
