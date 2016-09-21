#!/bin/bash

python /app/create_db.py

# execute CMD
exec "$@"