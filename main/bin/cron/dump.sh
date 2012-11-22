#!/bin/bash
echo "*** dump.sh `date`"
source /home/biostar/www/production/live/biostar.env

set -ue

export VERSION=`python -c 'import main.server as m; print m.VERSION'`
export NAME=biostar-$VERSION-`date +\%Y-\%m-\%d`.sql.gz
export DB_BACKUP=$HOME/data/$NAME

echo "*** database dump to $DB_BACKUP"
/usr/bin/pg_dump -Fp -x -O -b -U $PG_USER $PG_DBNAME | gzip > $DB_BACKUP
