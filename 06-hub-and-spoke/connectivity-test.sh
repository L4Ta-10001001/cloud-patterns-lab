#!/bin/bash
exec > /dev/console 2>&1

echo "=== Hub-and-Spoke connectivity test ==="
echo "Source: Spoke A"
hostname -I
echo "Destination: Spoke B (10.30.1.196)"
ping -c 5 -W 3 10.30.1.196
echo "=== End of test ==="