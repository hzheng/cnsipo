#!/bin/bash

declare -r SCRIPT_NAME=$(basename "$BASH_SOURCE" .sh)

## exit the shell(default status code: 1) after printing the message to stderr
bail() {
    echo -ne "$1" >&2
    exit ${2-1}
}

## help message
declare -r HELP_MSG="Usage: $SCRIPT_NAME [OPTION]... d|t|a|u
  -h    display this help and exit
  -d    database name
  -p    database password
  -t    table prefix
  -u    database user name

  d     detail table
  t     transaction table
  a     auxiliary table
  u     UIG table
"

## print the usage and exit the shell(default status code: 2)
usage() {
    declare status=2
    if [[ "$1" =~ ^[0-9]+$ ]]; then
        status=$1
        shift
    fi
    bail "${1}$HELP_MSG" $status
}

dbname="cnsipo"
username="$USER"
tblprefix="patent_"

while getopts ":hd:p:t:u:" opt; do
    case $opt in
        h)
            usage 0;;
        d)
            dbname=$OPTARG
            ;;
        u)
            username=$OPTARG
            ;;
        p)
            pwd=$OPTARG
            ;;
        t)
            tblprefix=$OPTARG
            ;;
        \?)
            usage "Invalid option: -$OPTARG \n";;
    esac
done

shift $(($OPTIND - 1))
[[ "$#" -lt 1 ]] && usage "Too few arguments\n"

create_detail_db() {
    PGPASSWORD=$pwd psql $dbname $username << EOF
        CREATE TABLE ${tblprefix}detail(
            patent_id    SERIAL PRIMARY KEY  NOT NULL,
            app_no       varchar(28) UNIQUE,
            name         varchar(150),
            inventor     varchar(1200),
            applicant    varchar(500),
            app_date     date,
            app_pub_no   varchar(30),
            app_pub_date date,
            int_cl       varchar(2500),
            address      varchar(120),
            digest       varchar(2500),
            agency       varchar(120),
            agent        varchar(110)
    );
EOF
}

create_transaction_db() {
    PGPASSWORD=$pwd psql $dbname $username << EOF
        CREATE TABLE ${tblprefix}transaction(
            trans_id    SERIAL PRIMARY KEY  NOT NULL,
            app_no      varchar(28) NOT NULL REFERENCES ${tblprefix}detail (app_no),
            pub_date    date,
            data_type   varchar(200)
    );
EOF
}

create_aux_db() {
    PGPASSWORD=$pwd psql $dbname $username << EOF
        CREATE TABLE ${tblprefix}aux(
            aux_id      SERIAL PRIMARY KEY  NOT NULL,
            app_no      varchar(28) UNIQUE NOT NULL REFERENCES ${tblprefix}detail (app_no),
            app_year    smallint,
            country     varchar(20),
            state       varchar(10),
            collab      varchar(40),
            tech_flds   varchar(10),
            attrs       smallint
    );
EOF
}

create_uig_db() {
    PGPASSWORD=$pwd psql $dbname $username << EOF
        CREATE TABLE ${tblprefix}uig(
            uig_id      SERIAL PRIMARY KEY  NOT NULL,
            app_no      varchar(28) NOT NULL REFERENCES ${tblprefix}detail (app_no),
            org         varchar(50),
            org2        varchar(50),
            state       varchar(10),
            kind        char(1)
    );
EOF
}

case $1 in
    d)
        create_detail_db;;
    t)
        create_transaction_db;;
    a)
        create_aux_db;;
    u)
        create_uig_db;;
    *)
        usage "Invalid argument: $1\n";;
esac
