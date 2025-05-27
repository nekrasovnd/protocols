import sys
import socket
from scapy.all import IP, ICMP, sr1
from ipwhois import IPWhois, exceptions
import ipaddress

MAX_HOPS = 30
TIMEOUT = 2

def is_private(ip):
    return ipaddress.ip_address(ip).is_private

def get_whois_info(ip):
    try:
        obj = IPWhois(ip)
        res = obj.lookup_rdap(depth=1)
        netname = res.get('network', {}).get('name')
        asn = res.get('asn')
        country = res.get('network', {}).get('country')

        parts = []
        if netname:
            parts.append(netname)
        if asn and asn.isdigit():
            parts.append(asn)
        if country and country != 'EU':
            parts.append(country)

        return ', '.join(parts)
    except (exceptions.IPDefinedError, exceptions.HTTPLookupError, exceptions.ASNRegistryError):
        return None
    except Exception:
        return None

def traceroute(dest_name):
    try:
        dest_addr = socket.gethostbyname(dest_name)
    except socket.gaierror:
        print(f"{dest_name} is invalid")
        return

    print(f"Tracing route to {dest_name} [{dest_addr}]:\n")

    for ttl in range(1, MAX_HOPS + 1):
        pkt = IP(dst=dest_addr, ttl=ttl) / ICMP()
        reply = sr1(pkt, verbose=0, timeout=TIMEOUT)

        if reply is None:
            print(f"{ttl}. *\n")
            continue

        ip = reply.src
        print(f"{ttl}. {ip}")

        if is_private(ip):
            print("local\n")
        else:
            info = get_whois_info(ip)
            if info:
                print(f"{info}\n")
            else:
                print()

        if ip == dest_addr:
            break

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tracert-as.py <address>")
        sys.exit(1)

    try:
        traceroute(sys.argv[1])
    except PermissionError:
        print("Permission denied. Please run the script as administrator.")
    except Exception as e:
        print("Unexpected error:", str(e))
