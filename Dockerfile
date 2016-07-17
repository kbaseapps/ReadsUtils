FROM kbase/kbase:sdkbase.latest
MAINTAINER KBase Developer
# -----------------------------------------

# Insert apt-get instructions here to install
# any required dependencies for your module.

# RUN apt-get update

RUN cd /opt \
    && git clone https://github.com/kbase/jars \
    && mkdir lib \
    && cp jars/lib/jars/FastaValidator/FastaValidator-1.0.jar lib \
    && git clone https://github.com/statgen/libStatGen.git \
    && cd libStatGen \
    && make \
    && cd .. \
    && git clone https://github.com/statgen/fastQValidator.git \
    && cd fastQValidator \
    && make \
    && cd .. \
    && sudo apt-get install python-dev libffi-dev libssl-dev \
    && pip install pyopenssl ndg-httpsclient pyasn1 \
    && pip install requests --upgrade \
    && pip install 'requests[security]' --upgrade \
    && pip install six \
    && pip install ipython \
    && apt-get install nano

ENV PATH $PATH:/opt/fastQValidator/bin/

# -----------------------------------------

COPY ./ /kb/module
RUN mkdir -p /kb/module/work
RUN chmod 777 /kb/module

WORKDIR /kb/module

RUN make all

ENTRYPOINT [ "./scripts/entrypoint.sh" ]

CMD [ ]
