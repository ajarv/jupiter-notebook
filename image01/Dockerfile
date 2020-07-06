# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
FROM jupyter/datascience-notebook

LABEL maintainer="Jupyter Project <jupyter@googlegroups.com>"

USER root
COPY requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt

USER $NB_UID
