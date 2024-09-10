#!/bin/env bash

# Generates a root CA, intermediate CA and signs several end-user certificates with the latter.
# Validate intermediate CA certificate: openssl verify -CAfile ca-root.crt ca-intermediate.crt
# Validate edge certificate: openssl verify -CAfile ca-root.crt -untrusted ca-intermediate.crt party_0.crt

# sources:
# - https://superuser.com/q/126121
# - https://superuser.com/a/1590560
# - https://web.archive.org/web/20100504162138/http://www.ibm.com/developerworks/java/library/j-certgen/
# - https://security.stackexchange.com/a/176084

echo 00 > serial
touch index.txt

CA_ROOT=ca-root
# generate aes encrypted private key
openssl genpkey \
    -algorithm rsa \
    -out $CA_ROOT.pem
# create root CA certificate signing request
openssl req \
    -new \
    -nodes \
    -key $CA_ROOT.pem \
    -sha256 \
    -out $CA_ROOT.csr \
    -subj '/CN=My Root CA'
# create root CA certificate
openssl ca \
    -config ${PWD}/openssl.cnf \
    -extensions v3_ca \
    -extfile ./ssl-extensions-x509.cnf \
    -batch \
    -in $CA_ROOT.csr \
    -keyfile $CA_ROOT.pem \
    -out $CA_ROOT.crt \
    -selfsign

CA_INTERMEDIATE=ca-intermediate
# generate public key
openssl req \
    -new \
    -nodes \
    -out $CA_INTERMEDIATE.csr \
    -keyout $CA_INTERMEDIATE.pem \
    -subj "/CN=$CA_INTERMEDIATE"
# certify by root CA
openssl ca \
    -config ${PWD}/openssl.cnf \
    -batch \
    -extensions v3_ca \
    -extfile ./ssl-extensions-x509.cnf \
    -create_serial \
    -cert $CA_ROOT.crt \
    -keyfile $CA_ROOT.pem \
    -out $CA_INTERMEDIATE.crt \
    -in $CA_INTERMEDIATE.csr

# certificate for players
for PARTY in party_{0..1}; do
    # create public key
    openssl req \
        -new \
        -nodes \
        -out $PARTY.csr \
        -keyout $PARTY.pem \
        -subj "/CN=$PARTY"
    # certify by intermediate CA
    openssl ca \
        -config ${PWD}/openssl.cnf \
        -batch \
        -create_serial \
        -keyfile $CA_INTERMEDIATE.pem \
        -cert $CA_INTERMEDIATE.crt \
        -out $PARTY.crt \
        -in $PARTY.csr
done

# Single file with certificate chain for python ssl
cat $CA_ROOT.crt $CA_INTERMEDIATE.crt > ca-combined.crt

rm *.csr *.txt* serial* 0*.pem
