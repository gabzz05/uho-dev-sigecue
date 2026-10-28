#!/bin/sh
# RG-006: nginx necesita un certificado para servir HTTPS.
# En producción se monta el de la UHO en /etc/nginx/certs (sigecue.crt y sigecue.key).
# Si no hay ninguno, se genera uno autofirmado para poder probar en un entorno limpio
# (el navegador avisará de que no es de confianza).
set -e
CERTS=/etc/nginx/certs
mkdir -p "$CERTS"
if [ ! -f "$CERTS/sigecue.crt" ] || [ ! -f "$CERTS/sigecue.key" ]; then
    echo "No hay certificado en $CERTS: se genera uno autofirmado (solo para pruebas)."
    openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
        -subj "/CN=${SERVER_NAME:-localhost}" \
        -keyout "$CERTS/sigecue.key" -out "$CERTS/sigecue.crt" 2>/dev/null
fi
