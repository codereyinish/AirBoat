#!/bin/bash
echo "____________________________________________"
echo "    Airboat"
echo "____________________________________________"
echo ""
echo "Safari setup (one time only):"
echo " Settings --> Advanced  --> Proxies --> HTTP Proxy"
echo " Server: 127.0.0.1        Port: 8080"
echo ""
echo " Safari -> Develop -> Allow JavaScript from Apple Events"
echo "________________________________________"
echo ""

mitmdump -s addon.py --listen-port 8080 &
python window.py
