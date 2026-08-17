#!/bin/bash

echo "Starting log rotation process..."

find ../logs -name "*.log" -mtime +7 -exec gzip {} \;
