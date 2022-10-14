from centos:7.2.1511
maintainer Kerwin Piao <piaoyuankui@gmail.com>

run curl http://mirrors.163.com/.help/CentOS7-Base-163.repo > /etc/yum.repos.d/CentOS-Base.repo
run yum clean all
run yum install -y epel-release
run yum install -y python python-devel python-pip ipython \
    && yum install -y git wget ctags vim curl axel \
    && yum install -y openssl-devel libffi-devel libev-devel \
    && yum install -y glibc-devel gcc-c++ gcc cpp make \
    && yum install -y postgresql-devel \
    && yum install -y libtiff-devel libjpeg-devel libzip-devel freetype-devel lcms2-devel libwebp-devel tcl-devel tk-devel \
    && yum install -y libxml2 libxml2-devel libxslt libxslt-devel \
    && yum install -y supervisor \
    && yum install -y rpm-build \
    && yum install -y yum-utils \
    && yum install -y gettext \
    && yum install -y mysql redis

run ["/bin/bash", "-c", "wget -O - https://bootstrap.pypa.io/get-pip.py | python"]
run pip install -U setuptools
run pip install tox

run yum install -y mariadb-server mysql-devel
run /usr/libexec/mariadb-prepare-db-dir
