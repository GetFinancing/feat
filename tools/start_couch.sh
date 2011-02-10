#!/bin/bash

rm -rf /tmp/couchdb
mkdir -p /tmp/couchdb/db

echo "
[couchdb]
database_dir = /tmp/couchdb/db
view_index_dir = /tmp/couchdb/db

[httpd]
bind_address = ${HOST:-127.0.0.1}
port = ${PORT:-5984}

[log]
file = /tmp/couchdb/couchdb.log
" > /tmp/local.ini

/usr/bin/couchdb -a /tmp/local.ini