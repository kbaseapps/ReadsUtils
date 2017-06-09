FROM kbase/kbase:sdkbase.latest
MAINTAINER KBase Developer
# -----------------------------------------

# Insert apt-get instructions here to install
# any required dependencies for your module.

# RUN apt-get update

RUN sudo apt-get install python-dev libffi-dev libssl-dev
RUN pip install cffi --upgrade
RUN pip install pyopenssl --upgrade
RUN pip install ndg-httpsclient --upgrade
RUN pip install pyasn1 --upgrade
RUN pip install requests --upgrade \
    && pip install 'requests[security]' --upgrade

# Debug tools = all below six
RUN pip install six \
    && pip install ipython==5.3.0 \
    && apt-get install nano \
    && apt-get install tree

RUN cd /opt \
    && git clone https://github.com/kbase/jars \
    && mkdir lib \
    && cp jars/lib/jars/FastaValidator/FastaValidator-1.0.jar lib

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
